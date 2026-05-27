import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import crud
import models
import schemas
from database import SessionLocal
from services.lead_finder import search_law_firms
from services.email_generator import generate_outreach_email
from services.email_sender import send_email

router = APIRouter(prefix="/firms", tags=["firms"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=schemas.FirmResponse)
def add_firm(firm: schemas.FirmCreate, db: Session = Depends(get_db)):
    return crud.create_firm(db, firm)


@router.get("/", response_model=list[schemas.FirmResponse])
def list_firms(db: Session = Depends(get_db)):
    return crud.get_firms(db)


@router.get("/stats/")
def get_firm_stats(db: Session = Depends(get_db)):
    total_firms = db.query(models.Firm).count()
    firms_with_emails = db.query(models.Firm).filter(models.Firm.email.isnot(None)).count()
    firms_without_emails = db.query(models.Firm).filter(models.Firm.email.is_(None)).count()
    emails_sent = db.query(models.Firm).filter(models.Firm.status == "Email Sent").count()
    not_contacted = db.query(models.Firm).filter(models.Firm.status == "Not Contacted").count()
    failed_logs = db.query(models.EmailLog).filter(models.EmailLog.status == "Failed").count()
    sent_logs = db.query(models.EmailLog).filter(models.EmailLog.status == "Sent").count()

    return {
        "total_firms": total_firms,
        "firms_with_emails": firms_with_emails,
        "firms_without_emails": firms_without_emails,
        "emails_sent": emails_sent,
        "not_contacted": not_contacted,
        "sent_logs": sent_logs,
        "failed_logs": failed_logs
    }


@router.get("/email-logs/")
def get_email_logs(db: Session = Depends(get_db)):
    return db.query(models.EmailLog).all()


@router.get("/search/")
def search_firms(keyword: str, city: str, state: str):
    return search_law_firms(keyword, city, state)


@router.post("/search-and-save/", response_model=list[schemas.FirmResponse])
def search_and_save_firms(keyword: str, city: str, state: str, db: Session = Depends(get_db)):
    results = search_law_firms(keyword, city, state)
    saved_firms = []

    for firm in results:
        firm_data = schemas.FirmCreate(
            firm_name=firm.get("firm_name"),
            practice_area=keyword,
            city=city,
            phone=firm.get("phone"),
            website=firm.get("website"),
            email=firm.get("email"),
            address=firm.get("address"),
            rating=firm.get("rating"),
            business_status=firm.get("business_status"),
            status="Not Contacted"
        )

        saved_firm = crud.create_firm(db, firm_data)
        saved_firms.append(saved_firm)

    return saved_firms


@router.get("/{firm_id}/generate-email/")
def generate_email_for_firm(firm_id: int, db: Session = Depends(get_db)):
    firm = db.query(models.Firm).filter(models.Firm.id == firm_id).first()

    if not firm:
        return {"success": False, "error": "Firm not found"}

    return generate_outreach_email(
        firm_name=firm.firm_name,
        city=firm.city,
        practice_area=firm.practice_area
    )


@router.post("/{firm_id}/send-test-email/")
def send_test_email_for_firm(firm_id: int, test_email: str, db: Session = Depends(get_db)):
    firm = db.query(models.Firm).filter(models.Firm.id == firm_id).first()

    if not firm:
        return {"success": False, "error": "Firm not found"}

    generated = generate_outreach_email(
        firm_name=firm.firm_name,
        city=firm.city,
        practice_area=firm.practice_area
    )

    send_email(
        to_email=test_email,
        subject=generated["subject"],
        body=generated["body"]
    )

    return {
        "success": True,
        "message": f"Test email sent to {test_email}"
    }


@router.post("/{firm_id}/send-outreach/")
def send_outreach_email(firm_id: int, db: Session = Depends(get_db)):
    firm = db.query(models.Firm).filter(models.Firm.id == firm_id).first()

    if not firm:
        return {"success": False, "error": "Firm not found"}

    if not firm.email:
        return {"success": False, "error": "No email for this firm"}

    if firm.status == "Email Sent":
        return {"success": False, "error": "Email already sent to this firm"}

    generated = generate_outreach_email(
        firm_name=firm.firm_name,
        city=firm.city,
        practice_area=firm.practice_area
    )

    try:
        send_email(
            to_email=firm.email,
            subject=generated["subject"],
            body=generated["body"]
        )

        log = models.EmailLog(
            firm_id=firm.id,
            firm_name=firm.firm_name,
            email=firm.email,
            subject=generated["subject"],
            status="Sent",
            error_message=None
        )

        db.add(log)
        firm.status = "Email Sent"
        db.commit()

        return {
            "success": True,
            "message": f"Outreach email sent to {firm.firm_name}",
            "email": firm.email
        }

    except Exception as e:
        log = models.EmailLog(
            firm_id=firm.id,
            firm_name=firm.firm_name,
            email=firm.email,
            subject=generated["subject"],
            status="Failed",
            error_message=str(e)
        )

        db.add(log)
        db.commit()

        return {
            "success": False,
            "error": str(e)
        }


@router.post("/send-batch-outreach/")
def send_batch_outreach(limit: int = 3, delay_seconds: int = 10, db: Session = Depends(get_db)):
    firms = db.query(models.Firm).filter(
        models.Firm.email.isnot(None),
        models.Firm.status != "Email Sent"
    ).limit(limit).all()

    sent = []
    failed = []

    for firm in firms:
        generated = generate_outreach_email(
            firm_name=firm.firm_name,
            city=firm.city,
            practice_area=firm.practice_area
        )

        try:
            send_email(
                to_email=firm.email,
                subject=generated["subject"],
                body=generated["body"]
            )

            log = models.EmailLog(
                firm_id=firm.id,
                firm_name=firm.firm_name,
                email=firm.email,
                subject=generated["subject"],
                status="Sent",
                error_message=None
            )

            db.add(log)
            firm.status = "Email Sent"
            db.commit()

            sent.append({
                "firm": firm.firm_name,
                "email": firm.email
            })

            time.sleep(delay_seconds)

        except Exception as e:
            log = models.EmailLog(
                firm_id=firm.id,
                firm_name=firm.firm_name,
                email=firm.email,
                subject=generated["subject"],
                status="Failed",
                error_message=str(e)
            )

            db.add(log)
            db.commit()

            failed.append({
                "firm": firm.firm_name,
                "email": firm.email,
                "error": str(e)
            })

    return {
        "sent_count": len(sent),
        "failed_count": len(failed),
        "sent": sent,
        "failed": failed
    }
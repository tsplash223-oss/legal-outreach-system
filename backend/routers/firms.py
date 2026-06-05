import json
import shutil
import time
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

import crud
import models
import schemas
from database import DATABASE_PATH, SessionLocal
from services.lead_finder import GoogleMapsConfigurationError, GoogleMapsSearchError, search_law_firms
from services.email_generator import DEFAULT_BODY_TEXT, DEFAULT_SUBJECT, generate_outreach_email, is_official_template
from services.email_sender import send_email
from services.gmail_reply_tracker import check_gmail_replies

router = APIRouter(tags=["firms"])

FOLLOW_UP_SUBJECT = "Follow-Up - Green Light Drivers Ed & DUI School LLC"
FOLLOW_UP_SIGNATURE_IMAGE_HTML = '<img src="cid:signature_image" alt="Signature" style="width:140px; max-width:140px; display:block; margin:8px 0 4px 0;">'
FOLLOW_UP_BODY_TEXT = """Dear {firm_name} Team,

I wanted to follow up on our previous message introducing Green Light Drivers Ed & DUI School LLC.

We provide DDS-approved defensive driving courses, DUI/Risk Reduction programs, Joshua's Law driver education, road test preparation, and other driving-related services that may be useful for clients who need court-related or compliance-related driving programs.

Please let us know if your office would like additional information about our services.

Sincerely,

{{signature_image}}

Manager
Green Light Drivers Ed & DUI School LLC"""
FOLLOW_UP_EXCLUDED_STATUSES = {"Replied", "Interested", "Meeting Scheduled", "Partner", "Not Interested"}
CONTACTED_STATUSES = {"Email Sent", "Replied", "Interested", "Meeting Scheduled", "Partner", "Not Interested"}
FOLLOW_UP_SETTINGS_PATH = Path(__file__).resolve().parents[1] / "follow_up_settings.json"
DEFAULT_AUTO_FOLLOW_UP_SETTINGS = {
    "enabled": False,
    "daily_limit": 5,
    "delay_seconds": 10,
}
CAMPAIGN_RESET_TABLES = [
    "firms",
    "email_logs",
    "replies",
    "follow_up_logs",
    "campaign_logs",
    "newsletter_logs",
]
CAMPAIGN_RESET_DELETE_ORDER = [
    "email_logs",
    "replies",
    "follow_up_logs",
    "campaign_logs",
    "newsletter_logs",
    "firms",
]


def clean_auto_follow_up_settings(settings: dict | None):
    settings = settings or {}

    return {
        "enabled": bool(settings.get("enabled", DEFAULT_AUTO_FOLLOW_UP_SETTINGS["enabled"])),
        "daily_limit": max(1, min(50, int(settings.get("daily_limit", DEFAULT_AUTO_FOLLOW_UP_SETTINGS["daily_limit"]) or 5))),
        "delay_seconds": max(0, min(300, int(settings.get("delay_seconds", DEFAULT_AUTO_FOLLOW_UP_SETTINGS["delay_seconds"]) or 10))),
    }


def load_auto_follow_up_settings():
    if not FOLLOW_UP_SETTINGS_PATH.exists():
        return DEFAULT_AUTO_FOLLOW_UP_SETTINGS.copy()

    try:
        return clean_auto_follow_up_settings(json.loads(FOLLOW_UP_SETTINGS_PATH.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return DEFAULT_AUTO_FOLLOW_UP_SETTINGS.copy()


def save_auto_follow_up_settings(settings: dict):
    cleaned_settings = clean_auto_follow_up_settings(settings)
    FOLLOW_UP_SETTINGS_PATH.write_text(
        json.dumps(cleaned_settings, indent=2),
        encoding="utf-8"
    )
    return cleaned_settings


def ensure_follow_up_columns(db: Session):
    columns = {
        row[1]
        for row in db.execute(text("PRAGMA table_info(firms)")).fetchall()
    }

    if "last_contacted" not in columns:
        db.execute(text("ALTER TABLE firms ADD COLUMN last_contacted DATETIME"))

    if "follow_up_count" not in columns:
        db.execute(text("ALTER TABLE firms ADD COLUMN follow_up_count INTEGER DEFAULT 0"))

    if "last_follow_up_date" not in columns:
        db.execute(text("ALTER TABLE firms ADD COLUMN last_follow_up_date DATETIME"))

    db.commit()


def get_db():
    db = SessionLocal()
    try:
        ensure_follow_up_columns(db)
        yield db
    finally:
        db.close()


def utc_now():
    return datetime.utcnow()


def utc_datetime_iso(value):
    if not value:
        return None

    return value.replace(microsecond=0).isoformat() + "Z"


def table_exists(db: Session, table_name: str):
    return db.execute(
        text("SELECT name FROM sqlite_master WHERE type = 'table' AND name = :table_name"),
        {"table_name": table_name}
    ).fetchone() is not None


def quoted_identifier(identifier: str):
    return '"' + identifier.replace('"', '""') + '"'


@router.post("/admin/reset-campaign-data")
def reset_campaign_data(db: Session = Depends(get_db)):
    backups_dir = DATABASE_PATH.parent / "backups"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"firms_backup_{timestamp}.db"
    backup_path = backups_dir / backup_name

    try:
        backups_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DATABASE_PATH, backup_path)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Backup failed. Campaign data was not cleared: {exc}"
        ) from exc

    deleted = {table_name: 0 for table_name in CAMPAIGN_RESET_TABLES}

    try:
        existing_tables = {
            table_name
            for table_name in CAMPAIGN_RESET_TABLES
            if table_exists(db, table_name)
        }

        for table_name in CAMPAIGN_RESET_DELETE_ORDER:
            if table_name not in existing_tables:
                continue

            quoted_table = quoted_identifier(table_name)
            deleted[table_name] = db.execute(text(f"SELECT COUNT(*) FROM {quoted_table}")).scalar() or 0
            db.execute(text(f"DELETE FROM {quoted_table}"))

        if table_exists(db, "sqlite_sequence") and existing_tables:
            for table_name in CAMPAIGN_RESET_TABLES:
                if table_name in existing_tables:
                    db.execute(text("DELETE FROM sqlite_sequence WHERE name = :table_name"), {"table_name": table_name})

        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Backup was created, but campaign data could not be cleared: {exc}"
        ) from exc

    return {
        "success": True,
        "message": "Campaign data cleared successfully. Backup created first.",
        "backup_file": f"backups/{backup_name}",
        "deleted": deleted,
    }


def format_datetime(value):
    return utc_datetime_iso(value)


def days_since(value):
    if not value:
        return None

    return max(0, (utc_now() - value).days)


def latest_sent_log_date(db: Session, firm_id: int):
    latest_log = db.query(models.EmailLog).filter(
        models.EmailLog.firm_id == firm_id,
        models.EmailLog.status == "Sent"
    ).order_by(models.EmailLog.sent_at.desc()).first()

    return latest_log.sent_at if latest_log else None


def follow_up_reference_date(firm, db: Session):
    follow_up_count = firm.follow_up_count or 0

    if follow_up_count == 0:
        return firm.last_contacted or latest_sent_log_date(db, firm.id)

    return firm.last_follow_up_date


def next_follow_up_type(follow_up_count: int):
    if follow_up_count == 0:
        return "Follow-Up #1"

    if follow_up_count == 1:
        return "Follow-Up #2"

    if follow_up_count == 2:
        return "Final Follow-Up"

    return None


def is_follow_up_eligible(firm, db: Session):
    if not firm.email:
        return False

    if firm.status in FOLLOW_UP_EXCLUDED_STATUSES:
        return False

    follow_up_count = firm.follow_up_count or 0

    if follow_up_count >= 3:
        return False

    reference_date = follow_up_reference_date(firm, db)
    elapsed_days = days_since(reference_date)

    if elapsed_days is None:
        return False

    if follow_up_count == 0:
        return firm.status == "Email Sent" and elapsed_days >= 5

    if follow_up_count == 1:
        return elapsed_days >= 10

    if follow_up_count == 2:
        return elapsed_days >= 14

    return False


def follow_up_prospect_item(firm, db: Session):
    reference_date = follow_up_reference_date(firm, db)

    return {
        "id": firm.id,
        "firm_name": firm.firm_name,
        "email": firm.email,
        "status": firm.status,
        "last_contacted": format_datetime(firm.last_contacted),
        "follow_up_count": firm.follow_up_count or 0,
        "last_follow_up_date": format_datetime(firm.last_follow_up_date),
        "days_since_contact": days_since(reference_date),
        "next_follow_up_type": next_follow_up_type(firm.follow_up_count or 0),
    }


def follow_up_email_body(firm_name: str):
    escaped_body = FOLLOW_UP_BODY_TEXT.format(firm_name=firm_name or "Prospect")
    escaped_body = escaped_body.replace("{signature_image}", FOLLOW_UP_SIGNATURE_IMAGE_HTML)
    return escaped_body.replace("\n", "<br>")


def update_initial_contact_tracking(firm, contacted_at):
    firm.status = "Email Sent"
    firm.last_contacted = contacted_at
    firm.follow_up_count = firm.follow_up_count or 0


def send_follow_up_for_firm(firm, db: Session):
    follow_up_type = next_follow_up_type(firm.follow_up_count or 0)
    body = follow_up_email_body(firm.firm_name)
    sent_at = utc_now()

    try:
        send_email(
            to_email=firm.email,
            subject=FOLLOW_UP_SUBJECT,
            body=body
        )

        log = models.EmailLog(
            firm_id=firm.id,
            firm_name=firm.firm_name,
            email=firm.email,
            subject=f"{FOLLOW_UP_SUBJECT} ({follow_up_type})",
            status="Sent",
            error_message=None,
            sent_at=sent_at
        )

        db.add(log)
        firm.last_contacted = sent_at
        firm.last_follow_up_date = sent_at
        firm.follow_up_count = (firm.follow_up_count or 0) + 1
        db.commit()

        return {
            "success": True,
            "firm_id": firm.id,
            "firm_name": firm.firm_name,
            "email": firm.email,
            "follow_up_type": follow_up_type,
            "follow_up_count": firm.follow_up_count,
            "last_follow_up_date": format_datetime(firm.last_follow_up_date),
            "message": f"{follow_up_type} sent to {firm.firm_name}",
        }

    except Exception as e:
        log = models.EmailLog(
            firm_id=firm.id,
            firm_name=firm.firm_name,
            email=firm.email,
            subject=f"{FOLLOW_UP_SUBJECT} ({follow_up_type})",
            status="Failed",
            error_message=str(e),
            sent_at=utc_now()
        )

        db.add(log)
        db.commit()

        return {
            "success": False,
            "firm_id": firm.id,
            "firm_name": firm.firm_name,
            "email": firm.email,
            "follow_up_type": follow_up_type,
            "error": str(e),
        }


def deactivate_templates(db: Session):
    db.query(models.EmailTemplate).update({models.EmailTemplate.is_active: False})


def restore_official_template_if_needed(db: Session):
    active_template = db.query(models.EmailTemplate).filter(models.EmailTemplate.is_active.is_(True)).first()

    if active_template and is_official_template(active_template.body_text):
        return active_template

    if active_template:
        active_template.name = active_template.name or "Main outreach letter"
        active_template.subject = DEFAULT_SUBJECT
        active_template.body_html = DEFAULT_BODY_TEXT
        db.commit()
        db.refresh(active_template)
        return active_template

    db_template = models.EmailTemplate(
        name="Main outreach letter",
        subject=DEFAULT_SUBJECT,
        body_html=DEFAULT_BODY_TEXT,
        is_active=True
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)

    return db_template


@router.get("/templates/", response_model=list[schemas.EmailTemplateResponse], tags=["templates"])
def list_email_templates(db: Session = Depends(get_db)):
    return db.query(models.EmailTemplate).order_by(models.EmailTemplate.updated_at.desc()).all()


@router.get("/templates/active/", response_model=schemas.EmailTemplateResponse | None, tags=["templates"])
def get_active_email_template(db: Session = Depends(get_db)):
    return restore_official_template_if_needed(db)


@router.post("/templates/", response_model=schemas.EmailTemplateResponse, tags=["templates"])
def create_email_template(template: schemas.EmailTemplateCreate, db: Session = Depends(get_db)):
    if template.is_active:
        deactivate_templates(db)

    db_template = models.EmailTemplate(
        name=template.name,
        subject=template.subject,
        body_html=template.body_text,
        is_active=template.is_active
    )

    db.add(db_template)
    db.commit()
    db.refresh(db_template)

    return db_template


@router.put("/templates/{template_id}/", response_model=schemas.EmailTemplateResponse, tags=["templates"])
def update_email_template(
    template_id: int,
    template: schemas.EmailTemplateUpdate,
    db: Session = Depends(get_db)
):
    db_template = db.query(models.EmailTemplate).filter(models.EmailTemplate.id == template_id).first()

    if not db_template:
        raise HTTPException(status_code=404, detail="Email template not found")

    updates = template.model_dump(exclude_unset=True)

    if updates.get("is_active") is True:
        deactivate_templates(db)

    for field, value in updates.items():
        setattr(db_template, field, value)

    db.commit()
    db.refresh(db_template)

    return db_template


@router.post("/templates/{template_id}/activate/", response_model=schemas.EmailTemplateResponse, tags=["templates"])
def activate_email_template(template_id: int, db: Session = Depends(get_db)):
    db_template = db.query(models.EmailTemplate).filter(models.EmailTemplate.id == template_id).first()

    if not db_template:
        raise HTTPException(status_code=404, detail="Email template not found")

    deactivate_templates(db)
    db_template.is_active = True
    db.commit()
    db.refresh(db_template)

    return db_template


@router.post("/firms/", response_model=schemas.FirmResponse)
def add_firm(firm: schemas.FirmCreate, db: Session = Depends(get_db)):
    return crud.create_firm(db, firm)


@router.get("/firms/", response_model=list[schemas.FirmResponse])
def list_firms(db: Session = Depends(get_db)):
    return crud.get_firms(db)


@router.put("/firms/{firm_id}/status", response_model=schemas.FirmResponse)
def update_firm_status(
    firm_id: int,
    status_update: schemas.FirmStatusUpdate,
    db: Session = Depends(get_db)
):
    firm = db.query(models.Firm).filter(models.Firm.id == firm_id).first()

    if not firm:
        raise HTTPException(status_code=404, detail="Firm not found")

    firm.status = status_update.status
    db.commit()
    db.refresh(firm)

    return firm


def clean_excel_value(value):
    if value is None:
        return ""

    try:
        if value != value:
            return ""
    except ValueError:
        return ""

    return str(value).strip()


def get_excel_row_value(row, column_name: str):
    if column_name not in row.index:
        return ""

    value = row[column_name]

    if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
        for item in value:
            cleaned_item = clean_excel_value(item)
            if cleaned_item:
                return cleaned_item
        return ""

    return clean_excel_value(value)


def excel_firm_item(firm):
    return {
        "id": firm.id,
        "firm_name": firm.firm_name,
        "email": firm.email,
        "phone": firm.phone,
        "website": firm.website,
        "city": firm.city,
        "practice_area": firm.practice_area,
        "status": firm.status,
    }


def excel_row_item(row_number: int, row_data: dict, reason: str):
    return {
        "row": row_number,
        "firm_name": row_data.get("firm_name", ""),
        "email": row_data.get("email", ""),
        "phone": row_data.get("phone", ""),
        "website": row_data.get("website", ""),
        "city": row_data.get("city", ""),
        "practice_area": row_data.get("practice_area", ""),
        "reason": reason,
    }


@router.post("/firms/import-excel/")
async def import_excel_firms(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""

    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Please upload a .xlsx Excel file.")

    contents = await file.read()

    try:
        import pandas as pd

        spreadsheet = pd.read_excel(BytesIO(contents), engine="openpyxl")
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="Excel import dependencies are missing. Install pandas, openpyxl, and python-multipart."
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to read Excel file: {exc}") from exc

    aliases = {
        "company": "firm_name",
        "company_name": "firm_name",
        "business_name": "firm_name",
        "firm": "firm_name",
        "firm_name": "firm_name",
        "email": "email",
        "email_address": "email",
        "contact_email": "email",
        "phone": "phone",
        "phone_number": "phone",
        "website": "website",
        "site": "website",
        "url": "website",
        "city": "city",
        "location": "city",
        "type": "practice_area",
        "prospect_type": "practice_area",
        "practice_area": "practice_area",
    }

    spreadsheet = spreadsheet.rename(
        columns={
            column: aliases.get(str(column).strip().lower(), str(column).strip().lower())
            for column in spreadsheet.columns
        }
    )

    expected_columns = ["firm_name", "email", "phone", "website", "city", "practice_area"]
    existing_emails = {
        email.lower()
        for (email,) in db.query(models.Firm.email).filter(models.Firm.email.isnot(None)).all()
        if email
    }

    imported = []
    duplicates = []
    missing_email = []
    blank_row_count = 0

    for index, row in spreadsheet.iterrows():
        row_data = {
            column: get_excel_row_value(row, column)
            for column in expected_columns
        }
        row_number = int(index) + 2

        if not any(row_data.values()):
            blank_row_count += 1
            continue

        email = row_data["email"]
        normalized_email = email.lower()

        if not email:
            missing_email.append(excel_row_item(row_number, row_data, "Missing email"))
            continue

        if normalized_email in existing_emails:
            duplicates.append(excel_row_item(row_number, row_data, "Duplicate email"))
            continue

        db_firm = models.Firm(
            firm_name=row_data["firm_name"] or email,
            email=email,
            phone=row_data["phone"],
            website=row_data["website"],
            city=row_data["city"] or "",
            practice_area=row_data["practice_area"] or "Imported Contact",
            status="Not Contacted",
        )

        db.add(db_firm)
        db.commit()
        db.refresh(db_firm)
        existing_emails.add(normalized_email)
        imported.append(excel_firm_item(db_firm))

    return {
        "imported_count": len(imported),
        "duplicate_count": len(duplicates),
        "missing_email_count": len(missing_email),
        "skipped_count": len(duplicates) + len(missing_email) + blank_row_count,
        "imported": imported,
        "duplicates": duplicates,
        "missing_email": missing_email,
    }


@router.get("/firms/stats/")
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


@router.get("/firms/analytics/", response_model=schemas.FirmAnalyticsResponse)
def get_firm_analytics(db: Session = Depends(get_db)):
    firms = db.query(models.Firm).all()
    sent_firm_ids = {
        firm_id
        for (firm_id,) in db.query(models.EmailLog.firm_id).filter(
            models.EmailLog.status == "Sent",
            models.EmailLog.firm_id.isnot(None)
        ).all()
    }
    contacted_statuses = {
        "Email Sent",
        "Replied",
        "Interested",
        "Meeting Scheduled",
        "Partner",
        "Not Interested",
    }

    total_prospects = len(firms)
    emails_sent = sum(
        1
        for firm in firms
        if firm.id in sent_firm_ids or firm.status in contacted_statuses
    )
    replies = sum(1 for firm in firms if firm.status in {"Replied", "Interested", "Meeting Scheduled", "Partner", "Not Interested"})
    interested = sum(1 for firm in firms if firm.status in {"Interested", "Meeting Scheduled", "Partner"})
    meetings_scheduled = sum(1 for firm in firms if firm.status in {"Meeting Scheduled", "Partner"})
    partners = sum(1 for firm in firms if firm.status == "Partner")
    not_interested = sum(1 for firm in firms if firm.status == "Not Interested")

    return {
        "total_prospects": total_prospects,
        "emails_sent": emails_sent,
        "replies": replies,
        "interested": interested,
        "meetings_scheduled": meetings_scheduled,
        "partners": partners,
        "not_interested": not_interested,
        "reply_rate": 0 if emails_sent == 0 else round((replies / emails_sent) * 100, 1),
        "interested_rate": 0 if replies == 0 else round((interested / replies) * 100, 1),
        "partner_conversion_rate": 0 if emails_sent == 0 else round((partners / emails_sent) * 100, 1),
    }


@router.get("/firms/email-logs/")
def get_email_logs(db: Session = Depends(get_db)):
    logs = db.query(models.EmailLog).order_by(models.EmailLog.sent_at.asc()).all()

    return [
        {
            "id": log.id,
            "firm_id": log.firm_id,
            "firm_name": log.firm_name,
            "email": log.email,
            "subject": log.subject,
            "status": log.status,
            "error_message": log.error_message,
            "sent_at": utc_datetime_iso(log.sent_at),
        }
        for log in logs
    ]


@router.get("/firms/check-replies/")
def check_replies(db: Session = Depends(get_db)):
    return check_gmail_replies(db)


@router.get("/firms/follow-ups/")
def get_follow_ups(db: Session = Depends(get_db)):
    firms = db.query(models.Firm).filter(models.Firm.email.isnot(None)).all()
    eligible_prospects = [
        follow_up_prospect_item(firm, db)
        for firm in firms
        if is_follow_up_eligible(firm, db)
    ]
    follow_ups_sent = sum(firm.follow_up_count or 0 for firm in firms)
    replied_count = db.query(models.Firm).filter(models.Firm.status == "Replied").count()
    contacted_count = db.query(models.Firm).filter(
        models.Firm.status.in_(["Email Sent", "Replied", "Interested", "Meeting Scheduled", "Partner", "Not Interested"])
    ).count()
    reply_rate = 0 if contacted_count == 0 else round((replied_count / contacted_count) * 100, 1)

    return {
        "eligible_count": len(eligible_prospects),
        "follow_ups_sent": follow_ups_sent,
        "reply_rate": f"{reply_rate}%",
        "prospects": eligible_prospects,
    }


@router.get("/firms/auto-follow-up-settings/")
def get_auto_follow_up_settings():
    return load_auto_follow_up_settings()


@router.post("/firms/auto-follow-up-settings/")
def update_auto_follow_up_settings(settings: dict = Body(...)):
    return save_auto_follow_up_settings(settings)


@router.post("/firms/run-auto-follow-ups/")
def run_auto_follow_ups(db: Session = Depends(get_db)):
    settings = load_auto_follow_up_settings()

    if not settings["enabled"]:
        return {
            "success": False,
            "sent_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "sent": [],
            "failed": [],
            "skipped": [],
            "message": "Automatic follow-ups are disabled.",
        }

    eligible_firms = [
        firm
        for firm in db.query(models.Firm).filter(models.Firm.email.isnot(None)).all()
        if is_follow_up_eligible(firm, db)
    ]
    daily_limit = settings["daily_limit"]
    delay_seconds = settings["delay_seconds"]
    firms_to_send = eligible_firms[:daily_limit]
    skipped = [
        {
            "id": firm.id,
            "firm_name": firm.firm_name,
            "email": firm.email,
            "reason": "Daily follow-up limit reached",
        }
        for firm in eligible_firms[daily_limit:]
    ]
    sent = []
    failed = []

    for index, firm in enumerate(firms_to_send):
        result = send_follow_up_for_firm(firm, db)

        if result["success"]:
            sent.append(result)
        else:
            failed.append(result)

        if index < len(firms_to_send) - 1 and delay_seconds > 0:
            time.sleep(delay_seconds)

    return {
        "success": True,
        "sent_count": len(sent),
        "failed_count": len(failed),
        "skipped_count": len(skipped),
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "message": f"Automatic follow-ups complete. Sent {len(sent)}, failed {len(failed)}, skipped {len(skipped)}.",
    }


@router.get("/firms/search/")
def search_firms(keyword: str, city: str, state: str):
    try:
        return search_law_firms(keyword, city, state)
    except GoogleMapsConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GoogleMapsSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/firms/search-and-save/", response_model=list[schemas.FirmResponse])
def search_and_save_firms(keyword: str, city: str, state: str, db: Session = Depends(get_db)):
    try:
        results = search_law_firms(keyword, city, state)
    except GoogleMapsConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GoogleMapsSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

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


def campaign_firm_item(firm, reason: str | None = None, error: str | None = None, outcome: str | None = None):
    item = {
        "id": firm.id,
        "firm": firm.firm_name,
        "email": firm.email,
        "city": firm.city,
        "status": firm.status,
    }

    if reason:
        item["reason"] = reason

    if error:
        item["error"] = error

    if outcome:
        item["outcome"] = outcome

    return item


def has_sent_email_log(db: Session, firm_id: int):
    return db.query(models.EmailLog.id).filter(
        models.EmailLog.firm_id == firm_id,
        models.EmailLog.status == "Sent"
    ).first() is not None


@router.post("/firms/run-campaign/")
def run_campaign(
    keyword: str,
    city: str,
    state: str,
    limit: int = 3,
    delay_seconds: int = 10,
    send_immediately: bool = True,
    db: Session = Depends(get_db)
):
    safe_limit = max(0, limit)
    safe_delay_seconds = max(0, delay_seconds)

    try:
        results = search_law_firms(keyword, city, state)
    except GoogleMapsConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GoogleMapsSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    saved_firms = []
    saved_count = 0
    skipped_no_email = []
    skipped_already_contacted = []
    skipped_other = []
    details = []

    for firm in results:
        firm_name = firm.get("firm_name")

        if not firm_name:
            item = {
                "firm": "Unknown firm",
                "email": firm.get("email"),
                "reason": "Missing firm name",
                "outcome": "skipped_other",
            }
            skipped_other.append(item)
            details.append(item)
            continue

        existing_firm = db.query(models.Firm).filter(
            models.Firm.firm_name == firm_name
        ).first()

        firm_data = schemas.FirmCreate(
            firm_name=firm_name,
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

        if not existing_firm:
            saved_count += 1

        saved_firms.append(saved_firm)

    eligible_firms = []

    for firm in saved_firms:
        if not firm.email:
            item = campaign_firm_item(firm, "No email found", outcome="skipped_no_email")
            skipped_no_email.append(item)
            details.append(item)
            continue

        if firm.status in CONTACTED_STATUSES or has_sent_email_log(db, firm.id):
            item = campaign_firm_item(firm, "Already contacted or Email Sent", outcome="skipped_already_contacted")
            skipped_already_contacted.append(item)
            details.append(item)
            continue

        eligible_firms.append(firm)

    sent = []
    failed = []
    firms_to_send = eligible_firms[:safe_limit] if send_immediately else []

    if send_immediately and safe_limit < len(eligible_firms):
        for firm in eligible_firms[safe_limit:]:
            item = campaign_firm_item(firm, "Campaign limit reached", outcome="skipped_other")
            skipped_other.append(item)
            details.append(item)

    if not send_immediately:
        for firm in eligible_firms:
            details.append(campaign_firm_item(firm, "Eligible for outreach", outcome="eligible"))

    if send_immediately:
        for index, firm in enumerate(firms_to_send):
            subject = "Green Light Drivers Ed & DUI School LLC Outreach"
            sent_at = utc_now()

            try:
                generated = generate_outreach_email(
                    firm_name=firm.firm_name,
                    city=firm.city,
                    practice_area=firm.practice_area
                )
                subject = generated["subject"]

                send_email(
                    to_email=firm.email,
                    subject=subject,
                    body=generated["body"]
                )

                log = models.EmailLog(
                    firm_id=firm.id,
                    firm_name=firm.firm_name,
                    email=firm.email,
                    subject=subject,
                    status="Sent",
                    error_message=None,
                    sent_at=sent_at
                )

                db.add(log)
                update_initial_contact_tracking(firm, sent_at)
                db.commit()

                item = campaign_firm_item(firm, "Email sent", outcome="sent")
                sent.append(item)
                details.append(item)

            except Exception as e:
                log = models.EmailLog(
                    firm_id=firm.id,
                    firm_name=firm.firm_name,
                    email=firm.email,
                    subject=subject,
                    status="Failed",
                    error_message=str(e),
                    sent_at=utc_now()
                )

                db.add(log)
                db.commit()

                item = campaign_firm_item(firm, "Email send failed", error=str(e), outcome="failed")
                failed.append(item)
                details.append(item)

            if index < len(firms_to_send) - 1 and safe_delay_seconds > 0:
                time.sleep(safe_delay_seconds)

    return {
        "searched_count": len(results),
        "saved_count": saved_count,
        "eligible_count": len(eligible_firms),
        "sent_count": len(sent),
        "failed_count": len(failed),
        "skipped_no_email": len(skipped_no_email),
        "skipped_already_contacted": len(skipped_already_contacted),
        "skipped_other": len(skipped_other),
        "skipped_count": len(skipped_no_email) + len(skipped_already_contacted) + len(skipped_other),
        "send_immediately": send_immediately,
        "sent": sent,
        "failed": failed,
        "skipped": [*skipped_no_email, *skipped_already_contacted, *skipped_other],
        "skipped_no_email_details": skipped_no_email,
        "skipped_already_contacted_details": skipped_already_contacted,
        "skipped_other_details": skipped_other,
        "eligible": [campaign_firm_item(firm) for firm in eligible_firms],
        "details": details,
    }


@router.get("/firms/{firm_id}/generate-email/")
def generate_email_for_firm(firm_id: int, db: Session = Depends(get_db)):
    firm = db.query(models.Firm).filter(models.Firm.id == firm_id).first()

    if not firm:
        return {"success": False, "error": "Firm not found"}

    return generate_outreach_email(
        firm_name=firm.firm_name,
        city=firm.city,
        practice_area=firm.practice_area
    )


@router.post("/firms/{firm_id}/send-test-email/")
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


@router.post("/firms/{firm_id}/send-outreach/")
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
        sent_at = utc_now()

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
            error_message=None,
            sent_at=sent_at
        )

        db.add(log)
        update_initial_contact_tracking(firm, sent_at)
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
            error_message=str(e),
            sent_at=utc_now()
        )

        db.add(log)
        db.commit()

        return {
            "success": False,
            "error": str(e)
        }


@router.post("/firms/{firm_id}/send-follow-up/")
def send_follow_up_email(firm_id: int, db: Session = Depends(get_db)):
    firm = db.query(models.Firm).filter(models.Firm.id == firm_id).first()

    if not firm:
        return {"success": False, "error": "Firm not found"}

    if not firm.email:
        return {"success": False, "error": "No email for this firm"}

    if not is_follow_up_eligible(firm, db):
        return {"success": False, "error": "This prospect is not eligible for a follow-up yet."}

    result = send_follow_up_for_firm(firm, db)

    if not result["success"]:
        return {"success": False, "error": result["error"]}

    return result


@router.post("/firms/send-batch-outreach/")
def send_batch_outreach(limit: int = 3, delay_seconds: int = 10, db: Session = Depends(get_db)):
    firms = db.query(models.Firm).filter(
        models.Firm.email.isnot(None),
        models.Firm.status != "Email Sent"
    ).limit(limit).all()

    sent = []
    failed = []

    for firm in firms:
        sent_at = utc_now()
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
                error_message=None,
                sent_at=sent_at
            )

            db.add(log)
            update_initial_contact_tracking(firm, sent_at)
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
                error_message=str(e),
                sent_at=utc_now()
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

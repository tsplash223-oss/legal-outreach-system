import re
import time
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import models
from audit import write_audit_log
from business_profiles import get_business_profile_or_default
from database import SessionLocal
from security import get_current_user, require_min_role
from services.email_sender import send_email

router = APIRouter(prefix="/newsletters", tags=["newsletters"], dependencies=[Depends(get_current_user)])

NEWSLETTER_LOG_PREFIX = "Newsletter:"
NEWSLETTER_BLOCKED_STATUSES = {"Not Interested", "Do Not Contact"}
VALID_NEWSLETTER_STATUSES = {
    "Partner",
    "Interested",
    "Replied",
    "Not Contacted",
    "Email Sent",
}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_valid_email(email: str | None):
    return bool(email and EMAIL_PATTERN.match(email.strip()))


def is_imported_contact(firm):
    return (firm.practice_area or "").strip().lower() == "imported contact"


def is_newsletter_eligible(firm):
    return is_valid_email(firm.email) and firm.status not in NEWSLETTER_BLOCKED_STATUSES


def contact_item(firm):
    eligible = is_newsletter_eligible(firm)
    category = firm.practice_area or ("Imported Contact" if is_imported_contact(firm) else "Prospect")

    return {
        "id": firm.id,
        "firm_name": firm.firm_name,
        "email": firm.email,
        "city": firm.city,
        "type_category": category,
        "status": firm.status or "Not Contacted",
        "newsletter_eligible": eligible,
        "source": "Imported" if is_imported_contact(firm) else "Prospect",
    }


def report_item(firm, reason: str | None = None, error: str | None = None):
    item = {
        "id": firm.id,
        "firm_name": firm.firm_name,
        "email": firm.email,
        "status": firm.status,
    }

    if reason:
        item["reason"] = reason

    if error:
        item["error"] = error

    return item


def html_paragraphs(text: str):
    blocks = [
        block.strip()
        for block in re.split(r"\n\s*\n", (text or "").strip())
        if block.strip()
    ]

    if not blocks:
        return "<p></p>"

    return "".join(
        f"<p>{escape_html(block).replace(chr(10), '<br>')}</p>"
        for block in blocks
    )


def escape_html(value):
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


def build_newsletter_html(title: str, body_text: str, call_to_action: str | None = None, business_profile=None):
    cta = (call_to_action or "").strip()
    cta_html = ""

    if cta:
        cta_html = f"""
          <div class="cta-box">
            <strong>Next Step</strong>
            <p>{escape_html(cta)}</p>
          </div>
        """

    profile_name = getattr(business_profile, "name", None) or "Green Light Drivers Ed & DUI School LLC"
    profile_address = escape_html(getattr(business_profile, "address", None) or "6110 McFarland Station Drive, Suite 703\nAlpharetta, GA 30004").replace("\n", "<br>")
    profile_phone = getattr(business_profile, "phone", None) or "(770) 685-1600"
    profile_email = getattr(business_profile, "sender_email", None) or "info@greenlightdrivers.com"
    profile_website = getattr(business_profile, "website", None) or "https://greenlightdrivers.com"

    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body {{
            margin: 0;
            padding: 0;
            color: #1f2937;
            background: #f5f7f9;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 15px;
            line-height: 1.65;
          }}
          .shell {{
            max-width: 680px;
            margin: 0 auto;
            padding: 24px;
          }}
          .newsletter {{
            background: #ffffff;
            border: 1px solid #e3e8ee;
            border-radius: 8px;
            overflow: hidden;
          }}
          .header {{
            padding: 24px;
            color: #ffffff;
            background: #4d8f2a;
          }}
          .header span {{
            display: block;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
          }}
          .header h1 {{
            margin: 6px 0 0;
            font-size: 24px;
            line-height: 1.2;
          }}
          .content {{
            padding: 24px;
          }}
          .content p {{
            margin: 0 0 16px;
          }}
          .cta-box {{
            margin: 20px 0;
            padding: 16px;
            border: 1px solid #d9ead2;
            border-radius: 8px;
            background: #edf6e9;
          }}
          .cta-box strong {{
            color: #376d1e;
          }}
          .business-footer {{
            padding: 18px 24px;
            color: #4b5563;
            background: #fbfcfd;
            border-top: 1px solid #e3e8ee;
            font-size: 13px;
          }}
          .compliance-footer {{
            padding: 16px 24px 22px;
            color: #68717d;
            font-size: 12px;
          }}
        </style>
      </head>
      <body>
        <div class="shell">
          <div class="newsletter">
            <div class="header">
              <span>Green Light Newsletter</span>
              <h1>{escape_html(title or "Green Light Update")}</h1>
            </div>
            <div class="content">
              {html_paragraphs(body_text)}
              {cta_html}
            </div>
            <div class="business-footer">
              <strong>{escape_html(profile_name)}</strong><br>
              {profile_address}<br>
              Phone: {escape_html(profile_phone)}<br>
              Email: {escape_html(profile_email)}<br>
              Website: <a href="{escape_html(profile_website)}">{escape_html(profile_website)}</a>
            </div>
            <div class="compliance-footer">
              You are receiving this message from {escape_html(profile_name)}.<br>
              To opt out of future promotional emails, reply with "Unsubscribe".
            </div>
          </div>
        </div>
      </body>
    </html>
    """


def selected_newsletter_contacts(db: Session, payload: dict):
    audience = payload.get("audience", "selected")
    contact_ids = payload.get("contact_ids") or []
    statuses = payload.get("statuses") or []
    query = db.query(models.Firm)

    if audience == "all":
        return query.filter(models.Firm.email.isnot(None)).order_by(models.Firm.firm_name.asc()).all()

    if audience == "imported":
        return query.filter(
            models.Firm.email.isnot(None),
            models.Firm.practice_area == "Imported Contact"
        ).order_by(models.Firm.firm_name.asc()).all()

    if audience == "status":
        safe_statuses = [status for status in statuses if status in VALID_NEWSLETTER_STATUSES]
        if not safe_statuses:
            return []

        return query.filter(
            models.Firm.email.isnot(None),
            models.Firm.status.in_(safe_statuses)
        ).order_by(models.Firm.firm_name.asc()).all()

    if contact_ids:
        return query.filter(models.Firm.id.in_(contact_ids)).order_by(models.Firm.firm_name.asc()).all()

    return []


@router.get("/contacts/")
def get_newsletter_contacts(db: Session = Depends(get_db)):
    firms = db.query(models.Firm).order_by(models.Firm.firm_name.asc()).all()
    return [contact_item(firm) for firm in firms]


@router.get("/stats/")
def get_newsletter_stats(db: Session = Depends(get_db)):
    contacts = db.query(models.Firm).all()
    newsletter_logs = db.query(models.EmailLog).filter(
        models.EmailLog.subject.like(f"{NEWSLETTER_LOG_PREFIX}%")
    ).order_by(models.EmailLog.sent_at.desc()).all()
    sent_logs = [log for log in newsletter_logs if log.status == "Sent"]
    blocked_count = sum(
        1
        for firm in contacts
        if firm.status in NEWSLETTER_BLOCKED_STATUSES
    )

    return {
        "total_newsletter_contacts": sum(1 for firm in contacts if is_newsletter_eligible(firm)),
        "newsletters_sent": len(sent_logs),
        "last_newsletter_sent": sent_logs[0].sent_at.isoformat() if sent_logs else None,
        "unsubscribed_do_not_contact": blocked_count,
    }


@router.post("/preview/")
def preview_newsletter(payload: dict = Body(...), db: Session = Depends(get_db)):
    title = (payload.get("title") or "").strip()
    subject = (payload.get("subject") or "").strip()
    body_text = (payload.get("body_text") or "").strip()

    if not title or not subject or not body_text:
        raise HTTPException(status_code=400, detail="Title, subject, and message body are required.")

    business_profile = get_business_profile_or_default(db, payload.get("business_profile_id"))

    return {
        "success": True,
        "subject": subject,
        "html": build_newsletter_html(title, body_text, payload.get("call_to_action"), business_profile),
    }


@router.post("/draft/")
def save_newsletter_draft(
    payload: dict = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_min_role("manager")),
):
    title = (payload.get("title") or "").strip()
    subject = (payload.get("subject") or "").strip()
    body_text = (payload.get("body_text") or "").strip()
    business_profile = get_business_profile_or_default(db, payload.get("business_profile_id"))

    if not title or not subject or not body_text:
        raise HTTPException(status_code=400, detail="Title, subject, and message body are required.")

    draft = models.NewsletterDraft(
        title=title,
        subject=subject,
        body_text=body_text,
        call_to_action=(payload.get("call_to_action") or "").strip() or None,
        business_profile_id=business_profile.id,
    )

    db.add(draft)
    write_audit_log(
        db,
        "template.newsletter_draft_created",
        actor=current_user,
        request=request,
        target_type="newsletter_draft",
        details={"title": title, "subject": subject, "business_profile_id": business_profile.id},
    )
    db.commit()
    db.refresh(draft)

    return {
        "success": True,
        "draft_id": draft.id,
        "message": "Newsletter draft saved.",
    }


@router.post("/send/")
def send_newsletter(
    payload: dict = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_min_role("manager")),
):
    title = (payload.get("title") or "").strip()
    subject = (payload.get("subject") or "").strip()
    body_text = (payload.get("body_text") or "").strip()
    confirmed = bool(payload.get("confirmed"))
    send_limit = max(1, min(250, int(payload.get("send_limit") or 25)))
    delay_seconds = max(0, min(300, int(payload.get("delay_seconds") or 10)))
    business_profile = get_business_profile_or_default(db, payload.get("business_profile_id"))

    if not confirmed:
        raise HTTPException(status_code=400, detail="Newsletter confirmation checkbox is required.")

    if not title or not subject or not body_text:
        raise HTTPException(status_code=400, detail="Title, subject, and message body are required.")

    candidates = selected_newsletter_contacts(db, payload)
    newsletter_html = build_newsletter_html(title, body_text, payload.get("call_to_action"), business_profile)
    sent = []
    failed = []
    skipped = []
    eligible = []

    seen_emails = set()
    for firm in candidates:
        normalized_email = (firm.email or "").strip().lower()

        if not is_valid_email(firm.email):
            skipped.append(report_item(firm, "Missing or invalid email"))
            continue

        if normalized_email in seen_emails:
            skipped.append(report_item(firm, "Duplicate email in selected audience"))
            continue

        if firm.status in NEWSLETTER_BLOCKED_STATUSES:
            skipped.append(report_item(firm, f"Status is {firm.status}"))
            continue

        seen_emails.add(normalized_email)
        eligible.append(firm)

    firms_to_send = eligible[:send_limit]

    for firm in eligible[send_limit:]:
        skipped.append(report_item(firm, "Newsletter send limit reached"))

    for index, firm in enumerate(firms_to_send):
        log_subject = f"{NEWSLETTER_LOG_PREFIX} {subject}"

        try:
            send_email(
                to_email=firm.email,
                subject=subject,
                body=newsletter_html,
                business_profile=business_profile,
            )

            db.add(models.EmailLog(
                firm_id=firm.id,
                firm_name=firm.firm_name,
                email=firm.email,
                subject=log_subject,
                status="Sent",
                error_message=None,
                business_profile_id=business_profile.id,
            ))
            write_audit_log(
                db,
                "campaign.newsletter_sent",
                actor=current_user,
                request=request,
                target_type="firm",
                target_id=firm.id,
                details={"email": firm.email, "subject": subject, "title": title, "business_profile_id": business_profile.id},
            )
            db.commit()
            sent.append(report_item(firm))
        except Exception as exc:
            db.add(models.EmailLog(
                firm_id=firm.id,
                firm_name=firm.firm_name,
                email=firm.email,
                subject=log_subject,
                status="Failed",
                error_message=str(exc),
                business_profile_id=business_profile.id,
            ))
            write_audit_log(
                db,
                "campaign.newsletter_failed",
                actor=current_user,
                request=request,
                target_type="firm",
                target_id=firm.id,
                details={"email": firm.email, "subject": subject, "title": title, "error": str(exc), "business_profile_id": business_profile.id},
            )
            db.commit()
            failed.append(report_item(firm, error=str(exc)))

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
        "message": f"Newsletter complete. Sent {len(sent)}, failed {len(failed)}, skipped {len(skipped)}.",
        "completed_at": datetime.utcnow().isoformat(),
    }

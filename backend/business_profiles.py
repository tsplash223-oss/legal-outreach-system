from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

import models
from database import engine
from services.email_generator import DEFAULT_BODY_TEXT, DEFAULT_SUBJECT


DRIVERS_ED_PROFILE_NAME = "Green Light Drivers Ed & DUI School LLC"
HOPE_PROFILE_NAME = "Greenlight Hope Foundation"
GMAIL_PROFILE_NOT_CONFIGURED_MESSAGE = "Gmail credentials are not configured for this business profile."
HOPE_TEMPLATE_NAME = "Hope Foundation Introduction"
HOPE_TEMPLATE_SUBJECT = "Green Light Hope Foundation Inc."
HOPE_TEMPLATE_BODY = """Dear {Recipient Name},

We write to introduce Green Light Hope Foundation Inc (https://www.greenlighthopefoundation.com) to you as a Non-Profit Organization, founded and incorporated in the USA as a 501(c)(3), committed to building stronger, healthier, and safer communities through education, outreach, and compassionate support. From promoting safe driving and mental wellness to assisting vulnerable families and expanding access to essential resources, we work alongside individuals and communities to create lasting, positive change.

We welcome volunteers, professionals, and companies looking to contribute to safe driving, Mental wellness, homelessness solutions, family supports, and programs that promote the overall wellness of families.

We accept donations in all forms, including programs, resources, materials, and monetary donations, to help us achieve our goals year in and year out. We issue receipts for all donations, duly acknowledged and received for tax purposes, which are tax-deductible.

We ensure transparency, accountability, and proper documentation for your records.

Kindly support us.

Visit our website at https://www.greenlighthopefoundation.com.

Thank you.

CEO
Dr. Atilade O Oshoniyi,DM,MSM, MBA, B.Sc"""


DEFAULT_BUSINESS_PROFILES = [
    {
        "name": DRIVERS_ED_PROFILE_NAME,
        "sender_email": "info@greenlightdrivers.com",
        "phone": "(770) 685-1600",
        "website": "https://greenlightdrivers.com",
        "address": "6110 McFarland Station Drive, Suite 703\nAlpharetta, GA 30004",
        "signature_html": '<img src="cid:signature_image" alt="Signature" style="width:140px; max-width:140px; display:block; margin:8px 0 4px 0;">',
        "default_template_subject": DEFAULT_SUBJECT,
        "default_template_body": DEFAULT_BODY_TEXT,
        "gmail_credentials_env_key": "GREENLIGHT_GMAIL_CREDENTIALS_JSON",
        "gmail_token_env_key": "GREENLIGHT_GMAIL_TOKEN_JSON",
        "is_active": True,
    },
    {
        "name": HOPE_PROFILE_NAME,
        "sender_email": "",
        "phone": "",
        "website": "",
        "address": "",
        "signature_html": "",
        "default_template_subject": HOPE_TEMPLATE_SUBJECT,
        "default_template_body": HOPE_TEMPLATE_BODY,
        "gmail_credentials_env_key": "HOPE_GMAIL_CREDENTIALS_JSON",
        "gmail_token_env_key": "HOPE_GMAIL_TOKEN_JSON",
        "is_active": True,
    },
]


def default_profile_values(name: str):
    return next((profile for profile in DEFAULT_BUSINESS_PROFILES if profile["name"] == name), None)


def ensure_business_profile_columns(bind=engine):
    inspector = inspect(bind)

    if inspector.has_table("business_profiles"):
        return

    models.BusinessProfile.__table__.create(bind=bind, checkfirst=True)


def ensure_business_profile_foreign_key_columns(db: Session):
    inspector = inspect(db.bind)
    tables = {
        "firms": "business_profile_id",
        "email_logs": "business_profile_id",
        "email_templates": "business_profile_id",
        "newsletter_drafts": "business_profile_id",
        "audit_logs": "business_profile_id",
    }

    for table_name, column_name in tables.items():
        if not inspector.has_table(table_name):
            continue

        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if column_name in columns:
            continue

        db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} INTEGER"))

    db.commit()


def bootstrap_default_business_profiles():
    ensure_business_profile_columns()

    with Session(engine) as db:
        ensure_business_profile_foreign_key_columns(db)

        for profile_data in DEFAULT_BUSINESS_PROFILES:
            profile = db.query(models.BusinessProfile).filter(
                models.BusinessProfile.name == profile_data["name"]
            ).first()

            if profile:
                for field, value in profile_data.items():
                    if getattr(profile, field) in (None, "") and value not in (None, ""):
                        setattr(profile, field, value)
                continue

            db.add(models.BusinessProfile(**profile_data))

        db.flush()
        default_profile = db.query(models.BusinessProfile).filter(
            models.BusinessProfile.name == DRIVERS_ED_PROFILE_NAME
        ).first()
        if default_profile:
            for model in (models.Firm, models.EmailLog, models.EmailTemplate, models.NewsletterDraft, models.AuditLog):
                db.query(model).filter(model.business_profile_id.is_(None)).update(
                    {model.business_profile_id: default_profile.id}
                )

        hope_profile = db.query(models.BusinessProfile).filter(
            models.BusinessProfile.name == HOPE_PROFILE_NAME
        ).first()
        if hope_profile:
            hope_profile.default_template_subject = HOPE_TEMPLATE_SUBJECT
            hope_profile.default_template_body = HOPE_TEMPLATE_BODY

            hope_template = db.query(models.EmailTemplate).filter(
                models.EmailTemplate.business_profile_id == hope_profile.id,
                models.EmailTemplate.name == HOPE_TEMPLATE_NAME,
            ).first()
            active_hope_template = db.query(models.EmailTemplate).filter(
                models.EmailTemplate.business_profile_id == hope_profile.id,
                models.EmailTemplate.is_active.is_(True),
            ).first()
            should_activate_exact_template = (
                active_hope_template is None
                or active_hope_template.name == "Main outreach letter"
                or "community-focused work we support" in (active_hope_template.body_text or "")
            )

            if not hope_template:
                hope_template = models.EmailTemplate(
                    name=HOPE_TEMPLATE_NAME,
                    subject=HOPE_TEMPLATE_SUBJECT,
                    body_html=HOPE_TEMPLATE_BODY,
                    business_profile_id=hope_profile.id,
                    is_active=should_activate_exact_template,
                )
                db.add(hope_template)
            else:
                hope_template.subject = HOPE_TEMPLATE_SUBJECT
                hope_template.body_html = HOPE_TEMPLATE_BODY
                if should_activate_exact_template:
                    hope_template.is_active = True

            if should_activate_exact_template:
                db.query(models.EmailTemplate).filter(
                    models.EmailTemplate.business_profile_id == hope_profile.id,
                    models.EmailTemplate.name != HOPE_TEMPLATE_NAME,
                ).update({models.EmailTemplate.is_active: False})

        db.commit()


def get_default_business_profile(db: Session):
    profile = db.query(models.BusinessProfile).filter(
        models.BusinessProfile.name == DRIVERS_ED_PROFILE_NAME
    ).first()

    if profile:
        return profile

    profile_data = default_profile_values(DRIVERS_ED_PROFILE_NAME)
    profile = models.BusinessProfile(**profile_data)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_business_profile_or_default(db: Session, business_profile_id: int | None = None):
    if business_profile_id:
        profile = db.query(models.BusinessProfile).filter(
            models.BusinessProfile.id == business_profile_id,
            models.BusinessProfile.is_active.is_(True),
        ).first()
        if profile:
            return profile

    return get_default_business_profile(db)


def business_profile_display(profile: models.BusinessProfile):
    return {
        "id": profile.id,
        "name": profile.name,
        "sender_email": profile.sender_email,
        "phone": profile.phone,
        "website": profile.website,
        "address": profile.address,
        "signature_html": profile.signature_html,
        "default_template_subject": profile.default_template_subject,
        "default_template_body": profile.default_template_body,
        "gmail_credentials_env_key": profile.gmail_credentials_env_key,
        "gmail_token_env_key": profile.gmail_token_env_key,
        "is_active": profile.is_active,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }

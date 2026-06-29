from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey, Text
from database import Base
from datetime import datetime


class Firm(Base):
    __tablename__ = "firms"

    id = Column(Integer, primary_key=True, index=True)

    firm_name = Column(String, index=True)
    practice_area = Column(String)

    city = Column(String)

    phone = Column(String)

    website = Column(String)

    email = Column(String)

    address = Column(String)

    rating = Column(Float)

    business_status = Column(String)

    status = Column(String, default="Not Contacted")

    last_contacted = Column(DateTime, nullable=True)

    follow_up_count = Column(Integer, default=0)

    last_follow_up_date = Column(DateTime, nullable=True)

    notes = Column(Text, nullable=True)


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)

    firm_id = Column(Integer, ForeignKey("firms.id"))

    business_profile_id = Column(Integer, ForeignKey("business_profiles.id"), nullable=True)

    firm_name = Column(String)

    email = Column(String)

    subject = Column(String)

    status = Column(String)

    error_message = Column(String, nullable=True)

    sent_at = Column(DateTime, default=datetime.utcnow)


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)

    business_profile_id = Column(Integer, ForeignKey("business_profiles.id"), nullable=True)

    name = Column(String, index=True)

    subject = Column(String)

    body_html = Column(Text)

    is_active = Column(Boolean, default=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def body_text(self):
        return self.body_html

    @body_text.setter
    def body_text(self, value):
        self.body_html = value


class NewsletterDraft(Base):
    __tablename__ = "newsletter_drafts"

    id = Column(Integer, primary_key=True, index=True)

    business_profile_id = Column(Integer, ForeignKey("business_profiles.id"), nullable=True)

    title = Column(String, index=True)

    subject = Column(String)

    body_text = Column(Text)

    call_to_action = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="staff", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    sender_email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    signature_html = Column(Text, nullable=True)
    default_template_subject = Column(String, nullable=True)
    default_template_body = Column(Text, nullable=True)
    gmail_credentials_env_key = Column(String, nullable=True)
    gmail_token_env_key = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True, nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_email = Column(String, nullable=True)
    target_type = Column(String, nullable=True)
    target_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

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


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)

    firm_id = Column(Integer, ForeignKey("firms.id"))

    firm_name = Column(String)

    email = Column(String)

    subject = Column(String)

    status = Column(String)

    error_message = Column(String, nullable=True)

    sent_at = Column(DateTime, default=datetime.utcnow)


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)

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

    title = Column(String, index=True)

    subject = Column(String)

    body_text = Column(Text)

    call_to_action = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

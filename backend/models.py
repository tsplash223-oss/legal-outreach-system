from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
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
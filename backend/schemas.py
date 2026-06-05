from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime


VALID_FIRM_STATUSES = {
    "Not Contacted",
    "Email Sent",
    "Replied",
    "Interested",
    "Meeting Scheduled",
    "Partner",
    "Not Interested",
    "Do Not Contact",
}


class FirmBase(BaseModel):
    firm_name: str
    practice_area: str | None = None
    city: str | None = None
    phone: str | None = None
    website: str | None = None
    email: str | None = None
    status: str = "Not Contacted"

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str):
        if value not in VALID_FIRM_STATUSES:
            raise ValueError("Invalid firm status")

        return value


class FirmCreate(FirmBase):
    pass


class FirmStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str):
        if value not in VALID_FIRM_STATUSES:
            raise ValueError("Invalid firm status")

        return value


class FirmResponse(FirmBase):
    id: int
    last_contacted: datetime | None = None
    follow_up_count: int = 0
    last_follow_up_date: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FirmAnalyticsResponse(BaseModel):
    total_prospects: int
    emails_sent: int
    replies: int
    interested: int
    meetings_scheduled: int
    partners: int
    not_interested: int
    reply_rate: float
    interested_rate: float
    partner_conversion_rate: float


class EmailTemplateBase(BaseModel):
    name: str
    subject: str
    body_text: str
    is_active: bool = False


class EmailTemplateCreate(EmailTemplateBase):
    pass


class EmailTemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    body_text: str | None = None
    is_active: bool | None = None


class EmailTemplateResponse(EmailTemplateBase):
    id: int
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

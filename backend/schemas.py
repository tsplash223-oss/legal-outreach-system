from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from security import VALID_ROLES


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


class FirmNotesUpdate(BaseModel):
    notes: str | None = None


class FirmResponse(FirmBase):
    id: int
    last_contacted: datetime | None = None
    follow_up_count: int = 0
    last_follow_up_date: datetime | None = None
    notes: str | None = None

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


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserBase(BaseModel):
    email: str
    full_name: str | None = None
    role: str = "staff"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str):
        cleaned = (value or "").strip().lower()
        if "@" not in cleaned:
            raise ValueError("Valid email is required")
        return cleaned

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str):
        if value not in VALID_ROLES:
            raise ValueError("Invalid user role")
        return value


class UserCreate(UserBase):
    password: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None):
        if value is not None and len(value) < 10:
            raise ValueError("Password must be at least 10 characters")
        return value


class UserCreateResponse(BaseModel):
    user: "UserResponse"
    temporary_password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None

    @field_validator("role")
    @classmethod
    def validate_optional_role(cls, value: str | None):
        if value is not None and value not in VALID_ROLES:
            raise ValueError("Invalid user role")
        return value

    @field_validator("password")
    @classmethod
    def validate_optional_password(cls, value: str | None):
        if value is not None and len(value) < 10:
            raise ValueError("Password must be at least 10 characters")
        return value


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_login_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PasswordResetResponse(BaseModel):
    user: UserResponse
    temporary_password: str


class AuditLogResponse(BaseModel):
    id: int
    event_type: str
    actor_email: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    details: str | None = None
    ip_address: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

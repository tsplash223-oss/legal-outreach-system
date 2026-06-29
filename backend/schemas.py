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

    @field_validator("firm_name")
    @classmethod
    def validate_firm_name(cls, value: str):
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Company name is required")
        return cleaned

    @field_validator("practice_area", "city", "phone", "website", "email", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("email")
    @classmethod
    def validate_firm_email(cls, value: str | None):
        if value is not None and "@" not in value:
            raise ValueError("Valid email is required")
        return value

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
    business_profile_id: int | None = None


class EmailTemplateCreate(EmailTemplateBase):
    pass


class EmailTemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    body_text: str | None = None
    is_active: bool | None = None
    business_profile_id: int | None = None


class EmailTemplateResponse(EmailTemplateBase):
    id: int
    business_profile_id: int | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BusinessProfileBase(BaseModel):
    name: str
    sender_email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    signature_html: str | None = None
    default_template_subject: str | None = None
    default_template_body: str | None = None
    gmail_credentials_env_key: str | None = None
    gmail_token_env_key: str | None = None
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_business_profile_name(cls, value: str):
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Business profile name is required")
        return cleaned

    @field_validator(
        "sender_email",
        "phone",
        "website",
        "address",
        "signature_html",
        "default_template_subject",
        "default_template_body",
        "gmail_credentials_env_key",
        "gmail_token_env_key",
        mode="before",
    )
    @classmethod
    def normalize_optional_business_text(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class BusinessProfileCreate(BusinessProfileBase):
    pass


class BusinessProfileUpdate(BaseModel):
    name: str | None = None
    sender_email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    signature_html: str | None = None
    default_template_subject: str | None = None
    default_template_body: str | None = None
    gmail_credentials_env_key: str | None = None
    gmail_token_env_key: str | None = None
    is_active: bool | None = None


class BusinessProfileResponse(BusinessProfileBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BusinessProfileOption(BaseModel):
    id: int
    name: str
    is_default: bool = False


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

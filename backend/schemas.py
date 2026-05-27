from pydantic import BaseModel, ConfigDict


class FirmBase(BaseModel):
    firm_name: str
    practice_area: str | None = None
    city: str | None = None
    phone: str | None = None
    website: str | None = None
    email: str | None = None
    status: str = "Not Contacted"


class FirmCreate(FirmBase):
    pass


class FirmResponse(FirmBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import models
import schemas


class DuplicateFirmError(Exception):
    def __init__(self, message: str, existing_firm=None):
        super().__init__(message)
        self.existing_firm = existing_firm


def firm_profile_id(firm: schemas.FirmCreate):
    return getattr(firm, "business_profile_id", None)


def scoped_firm_query(db: Session, business_profile_id: int | None):
    query = db.query(models.Firm)
    if business_profile_id is not None:
        query = query.filter(models.Firm.business_profile_id == business_profile_id)
    return query


def find_existing_firm(db: Session, firm: schemas.FirmCreate):
    business_profile_id = firm_profile_id(firm)

    if firm.email:
        existing_email = scoped_firm_query(db, business_profile_id).filter(
            func.lower(models.Firm.email) == firm.email.lower()
        ).first()

        if existing_email:
            return existing_email

    query = scoped_firm_query(db, business_profile_id).filter(models.Firm.firm_name == firm.firm_name)

    if firm.city:
        query = query.filter(func.lower(models.Firm.city) == firm.city.lower())

    if firm.website:
        query = query.filter(func.lower(models.Firm.website) == firm.website.lower())

    existing_firm = query.first()

    if existing_firm:
        return existing_firm

    return scoped_firm_query(db, business_profile_id).filter(
        models.Firm.firm_name == firm.firm_name
    ).first()


def create_firm(db: Session, firm: schemas.FirmCreate):
    existing_firm = find_existing_firm(db, firm)

    if existing_firm:
        if firm.email and existing_firm.email and existing_firm.email.lower() == firm.email.lower():
            raise DuplicateFirmError("A prospect with this email already exists.", existing_firm=existing_firm)

        return existing_firm

    db_firm = models.Firm(**firm.model_dump())

    try:
        db.add(db_firm)
        db.commit()
        db.refresh(db_firm)
    except IntegrityError as exc:
        db.rollback()
        existing_firm = find_existing_firm(db, firm)
        if existing_firm:
            raise DuplicateFirmError("A prospect with this email already exists.", existing_firm=existing_firm) from exc
        raise DuplicateFirmError("A database conflict occurred while saving this prospect.") from exc

    return db_firm


def get_firms(db: Session, business_profile_id: int | None = None):
    return scoped_firm_query(db, business_profile_id).all()

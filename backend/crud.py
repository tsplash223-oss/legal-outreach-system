from sqlalchemy.orm import Session
from sqlalchemy import func
import models
import schemas


def create_firm(db: Session, firm: schemas.FirmCreate):
    if firm.email:
        existing_email = db.query(models.Firm).filter(
            func.lower(models.Firm.email) == firm.email.lower()
        ).first()

        if existing_email:
            raise ValueError("A prospect with this email already exists.")

    # Check if firm already exists
    existing_firm = db.query(models.Firm).filter(
        models.Firm.firm_name == firm.firm_name
    ).first()

    # If it exists, return it instead of creating duplicate
    if existing_firm:
        return existing_firm

    # Create new firm
    db_firm = models.Firm(**firm.model_dump())

    db.add(db_firm)
    db.commit()
    db.refresh(db_firm)

    return db_firm


def get_firms(db: Session):
    return db.query(models.Firm).all()

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import models
import schemas
from audit import write_audit_log
from business_profiles import DRIVERS_ED_PROFILE_NAME, get_default_business_profile
from security import get_current_user, get_db, require_role

router = APIRouter(
    prefix="/business-profiles",
    tags=["business-profiles"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=list[schemas.BusinessProfileResponse])
def list_business_profiles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    return db.query(models.BusinessProfile).order_by(models.BusinessProfile.name.asc()).all()


@router.get("/active-options/", response_model=list[schemas.BusinessProfileOption])
def active_business_profile_options(db: Session = Depends(get_db)):
    default_profile = get_default_business_profile(db)
    profiles = db.query(models.BusinessProfile).filter(
        models.BusinessProfile.is_active.is_(True)
    ).order_by(models.BusinessProfile.name.asc()).all()

    return [
        {
            "id": profile.id,
            "name": profile.name,
            "is_default": profile.id == default_profile.id or profile.name == DRIVERS_ED_PROFILE_NAME,
        }
        for profile in profiles
    ]


@router.post("/", response_model=schemas.BusinessProfileResponse)
def create_business_profile(
    payload: schemas.BusinessProfileCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    if db.query(models.BusinessProfile).filter(models.BusinessProfile.name == payload.name).first():
        raise HTTPException(status_code=409, detail="A business profile with this name already exists.")

    profile = models.BusinessProfile(**payload.model_dump())
    db.add(profile)
    db.flush()
    write_audit_log(
        db,
        "business_profile.created",
        actor=current_user,
        request=request,
        target_type="business_profile",
        target_id=profile.id,
        details={"name": profile.name},
    )
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/{profile_id}", response_model=schemas.BusinessProfileResponse)
def update_business_profile(
    profile_id: int,
    payload: schemas.BusinessProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    profile = db.query(models.BusinessProfile).filter(models.BusinessProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Business profile not found.")

    updates = payload.model_dump(exclude_unset=True)
    new_name = updates.get("name")
    if new_name:
        existing = db.query(models.BusinessProfile).filter(
            models.BusinessProfile.name == new_name,
            models.BusinessProfile.id != profile_id,
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="A business profile with this name already exists.")

    for field, value in updates.items():
        setattr(profile, field, value)

    write_audit_log(
        db,
        "business_profile.updated",
        actor=current_user,
        request=request,
        target_type="business_profile",
        target_id=profile.id,
        details={"fields": sorted(updates.keys())},
    )
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}")
def disable_business_profile(
    profile_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    profile = db.query(models.BusinessProfile).filter(models.BusinessProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Business profile not found.")

    if profile.name == DRIVERS_ED_PROFILE_NAME:
        raise HTTPException(status_code=400, detail="The default Green Light Drivers Ed profile cannot be disabled.")

    profile.is_active = False
    write_audit_log(
        db,
        "business_profile.disabled",
        actor=current_user,
        request=request,
        target_type="business_profile",
        target_id=profile.id,
        details={"name": profile.name},
    )
    db.commit()
    return {"success": True}

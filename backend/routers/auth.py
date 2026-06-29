from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import models
import schemas
from audit import write_audit_log
from business_profiles import get_business_profile_or_default
from security import (
    create_access_token,
    generate_temporary_password,
    get_current_user,
    get_db,
    hash_password,
    normalize_email,
    require_role,
    verify_password,
)

router = APIRouter(tags=["auth"])


def user_count(db: Session):
    return db.query(models.User.id).count()


def serialize_login(user: models.User):
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": user,
    }


@router.post("/auth/bootstrap", response_model=schemas.TokenResponse)
def bootstrap_first_admin(payload: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    if user_count(db) > 0:
        raise HTTPException(status_code=409, detail="Bootstrap is closed because users already exist.")

    if not payload.password:
        raise HTTPException(status_code=400, detail="Password is required for first admin bootstrap.")

    user = models.User(
        email=normalize_email(payload.email),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role="admin",
        is_active=True,
        last_login_at=datetime.utcnow(),
    )
    db.add(user)
    db.flush()
    write_audit_log(db, "user.bootstrap_admin", actor=user, request=request, target_type="user", target_id=user.id)
    write_audit_log(db, "auth.login", actor=user, request=request, details={"bootstrap": True})
    db.commit()
    db.refresh(user)
    return serialize_login(user)


@router.post("/auth/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = normalize_email(payload.email)
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        write_audit_log(db, "auth.login_failed", request=request, details={"email": email})
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not user.is_active:
        write_audit_log(db, "auth.login_disabled", actor=user, request=request)
        db.commit()
        raise HTTPException(status_code=403, detail="This user is disabled.")

    user.last_login_at = datetime.utcnow()
    write_audit_log(db, "auth.login", actor=user, request=request)
    db.commit()
    db.refresh(user)
    return serialize_login(user)


@router.get("/auth/me", response_model=schemas.UserResponse)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.get("/users/", response_model=list[schemas.UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.post("/users/", response_model=schemas.UserCreateResponse)
def create_user(
    payload: schemas.UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    email = normalize_email(payload.email)
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=409, detail="A user with this email already exists.")

    temporary_password = payload.password or generate_temporary_password()
    user = models.User(
        email=email,
        full_name=payload.full_name,
        password_hash=hash_password(temporary_password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    write_audit_log(
        db,
        "user.created",
        actor=current_user,
        request=request,
        target_type="user",
        target_id=user.id,
        details={"email": user.email, "role": user.role},
    )
    db.commit()
    db.refresh(user)
    return {"user": user, "temporary_password": temporary_password}


@router.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    payload: schemas.UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    updates = payload.model_dump(exclude_unset=True)
    updates.pop("password", None)
    previous_role = user.role
    previous_active = user.is_active

    if user.id == current_user.id and updates.get("is_active") is False:
        raise HTTPException(status_code=400, detail="Admins cannot disable their own account.")

    for field, value in updates.items():
        setattr(user, field, value)

    event_type = "user.updated"
    if "role" in updates and updates["role"] != previous_role:
        event_type = "user.role_changed"
    if "is_active" in updates and updates["is_active"] != previous_active:
        event_type = "user.disabled" if updates["is_active"] is False else "user.reactivated"

    write_audit_log(
        db,
        event_type,
        actor=current_user,
        request=request,
        target_type="user",
        target_id=user.id,
        details=updates,
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password", response_model=schemas.PasswordResetResponse)
def reset_user_password(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    temporary_password = generate_temporary_password()
    user.password_hash = hash_password(temporary_password)
    write_audit_log(
        db,
        "user.password_reset",
        actor=current_user,
        request=request,
        target_type="user",
        target_id=user.id,
        details={"email": user.email},
    )
    db.commit()
    db.refresh(user)
    return {"user": user, "temporary_password": temporary_password}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Admins cannot delete their own account.")

    write_audit_log(
        db,
        "user.deleted",
        actor=current_user,
        request=request,
        target_type="user",
        target_id=user.id,
        details={"email": user.email, "role": user.role},
    )
    db.delete(user)
    db.commit()
    return {"success": True}


@router.get("/audit-logs/", response_model=list[schemas.AuditLogResponse])
def list_audit_logs(
    limit: int = 200,
    business_profile_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    safe_limit = max(1, min(500, limit))
    query = db.query(models.AuditLog)
    if business_profile_id:
        business_profile = get_business_profile_or_default(db, business_profile_id)
        query = query.filter(models.AuditLog.business_profile_id == business_profile.id)
    return query.order_by(models.AuditLog.created_at.desc()).limit(safe_limit).all()

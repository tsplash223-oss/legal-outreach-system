import json

from fastapi import Request
from sqlalchemy.orm import Session

import models


def client_ip(request: Request | None):
    if not request:
        return None

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.client.host if request.client else None


def write_audit_log(
    db: Session,
    event_type: str,
    actor: models.User | None = None,
    request: Request | None = None,
    target_type: str | None = None,
    target_id: str | int | None = None,
    details: dict | None = None,
    business_profile_id: int | None = None,
):
    details = details or {}
    if business_profile_id is None:
        business_profile_id = details.get("business_profile_id")

    log = models.AuditLog(
        event_type=event_type,
        business_profile_id=business_profile_id,
        actor_user_id=actor.id if actor else None,
        actor_email=actor.email if actor else None,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        details=json.dumps(details, default=str),
        ip_address=client_ip(request),
    )
    db.add(log)
    return log

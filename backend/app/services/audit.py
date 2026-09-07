import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def write_audit(
    db: Session,
    *,
    case_id: uuid.UUID | None,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    details: dict | None = None,
) -> None:
    db.add(AuditLog(case_id=case_id, actor_user_id=actor_user_id, action=action, details=details))

"""Configurable planner-assignment algorithm (spec section 5).

Lives in code (not the database) so it's easy to extend later — e.g. add
"on duty today" or skill-based routing — without a migration.
AssignmentConfig only stores the knobs an admin can turn from the UI: mode
(manual/auto) and strategy.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.case import TreatmentPlanCase
from app.models.enums import AssignmentMode, AssignmentStrategy, CaseStatus, Role
from app.models.settings import AssignmentConfig
from app.models.user import User, UserRole
from app.services.audit import write_audit
from app.services.notifications import queue_notification

ACTIVE_STATUSES = [s for s in CaseStatus if s not in (CaseStatus.READY, CaseStatus.CONSULTATION_COMPLETED)]


def _eligible_planners(db: Session) -> list[User]:
    return (
        db.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(UserRole.role == Role.PLANNER, User.is_active.is_(True))
        )
        .scalars()
        .unique()
        .all()
    )


def _workload_by_planner(db: Session) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(TreatmentPlanCase.responsible_planner_user_id, func.count())
        .where(
            TreatmentPlanCase.responsible_planner_user_id.isnot(None),
            TreatmentPlanCase.status.in_(ACTIVE_STATUSES),
        )
        .group_by(TreatmentPlanCase.responsible_planner_user_id)
    ).all()
    return {planner_id: count for planner_id, count in rows}


def _last_auto_assigned_at(db: Session) -> dict[uuid.UUID, str]:
    rows = (
        db.execute(
            select(AuditLog.details, AuditLog.created_at)
            .where(AuditLog.action == "auto_assigned")
            .order_by(AuditLog.created_at.desc())
            .limit(200)
        )
        .all()
    )
    result: dict[uuid.UUID, str] = {}
    for details, created_at in rows:
        planner_id = details.get("planner_user_id") if details else None
        if planner_id and planner_id not in result:
            result[planner_id] = created_at.isoformat()
    return result


def auto_assign_planner(db: Session, case: TreatmentPlanCase) -> User | None:
    config = db.get(AssignmentConfig, 1)
    if not config or config.mode != AssignmentMode.AUTO:
        return None

    planners = _eligible_planners(db)
    if not planners:
        return None

    workload = _workload_by_planner(db)
    eligible = [p for p in planners if p.max_workload is None or workload.get(p.id, 0) < p.max_workload]
    if not eligible:
        return None

    if config.strategy == AssignmentStrategy.ROUND_ROBIN:
        last_assigned = _last_auto_assigned_at(db)
        chosen = min(eligible, key=lambda p: last_assigned.get(str(p.id), ""))
    else:  # LEAST_WORKLOAD (default)
        chosen = min(eligible, key=lambda p: workload.get(p.id, 0))

    case.responsible_planner_user_id = chosen.id
    from app.services.case_service import set_case_status  # local import: avoid circular import

    set_case_status(db, case, CaseStatus.ASSIGNED, reason="auto-assigned")

    write_audit(
        db,
        case_id=case.id,
        action="auto_assigned",
        details={"planner_user_id": str(chosen.id), "strategy": config.strategy.value},
    )
    queue_notification(db, case_id=case.id, recipient_user_id=chosen.id, type="case_assigned")

    return chosen

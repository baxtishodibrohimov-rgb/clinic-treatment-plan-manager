"""Reminder + overdue-escalation logic (spec section 7). Reads its schedule
entirely from ReminderRule — admins edit offsets from the UI, nothing here is
hardcoded. Every rule fires at most once per case (ReminderSentLog) so
re-running this on a tight schedule is always safe."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.case import TreatmentPlanCase
from app.models.enums import CaseStatus, ReminderTriggerType
from app.models.notification import ReminderRule, ReminderSentLog
from app.models.user import User
from app.services.assignment import ACTIVE_STATUSES
from app.services.audit import write_audit
from app.services.case_service import set_case_status
from app.services.notifications import queue_notification


def _mark_rule_sent(db: Session, case_id, rule_id) -> bool:
    """Returns True the first time a rule fires for a case, False on every
    later attempt (dedup via a unique constraint, so this is safe even if
    two workers race)."""
    db.add(ReminderSentLog(case_id=case_id, rule_id=rule_id))
    try:
        db.flush()
        return True
    except IntegrityError:
        db.rollback()
        return False


def _notify_admins(db: Session, case_id, notification_type: str) -> None:
    from app.models.enums import Role
    from app.models.user import UserRole

    admin_ids = db.execute(
        select(User.id).join(UserRole, UserRole.user_id == User.id).where(UserRole.role.in_([Role.ADMIN, Role.SUPER_ADMIN]))
    ).scalars().all()
    for admin_id in admin_ids:
        queue_notification(db, case_id=case_id, recipient_user_id=admin_id, type=notification_type)


def run_reminders(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    reminders_sent = 0
    cases_marked_overdue = 0

    rules = db.execute(select(ReminderRule).where(ReminderRule.is_active.is_(True))).scalars().all()

    for rule in rules:
        if rule.trigger_type == ReminderTriggerType.BEFORE_CONSULTATION:
            offset = timedelta(minutes=rule.offset_minutes or 0)
            window_start = now + offset - timedelta(minutes=5)
            window_end = now + offset + timedelta(minutes=5)

            cases = db.execute(
                select(TreatmentPlanCase).where(
                    TreatmentPlanCase.status.in_(ACTIVE_STATUSES),
                    TreatmentPlanCase.consultation_datetime.isnot(None),
                    TreatmentPlanCase.consultation_datetime >= window_start,
                    TreatmentPlanCase.consultation_datetime <= window_end,
                )
            ).scalars().all()

            for case in cases:
                if not _mark_rule_sent(db, case.id, rule.id):
                    continue
                if "planner" in rule.notify_roles and case.responsible_planner_user_id:
                    queue_notification(db, case_id=case.id, recipient_user_id=case.responsible_planner_user_id, type="reminder_before_consultation")
                if "doctor" in rule.notify_roles and case.primary_doctor_user_id:
                    queue_notification(db, case_id=case.id, recipient_user_id=case.primary_doctor_user_id, type="reminder_before_consultation")
                if "admin" in rule.notify_roles:
                    _notify_admins(db, case.id, "reminder_before_consultation")
                reminders_sent += 1
                db.commit()

        if rule.trigger_type == ReminderTriggerType.AFTER_DEADLINE:
            overdue_cases = db.execute(
                select(TreatmentPlanCase).where(
                    TreatmentPlanCase.status.in_(ACTIVE_STATUSES),
                    TreatmentPlanCase.deadline.isnot(None),
                    TreatmentPlanCase.deadline < now,
                )
            ).scalars().all()

            for case in overdue_cases:
                was_already_overdue = case.status == CaseStatus.OVERDUE
                set_case_status(db, case, CaseStatus.OVERDUE, reason="deadline passed")
                if not was_already_overdue:
                    cases_marked_overdue += 1

                if _mark_rule_sent(db, case.id, rule.id):
                    if "planner" in rule.notify_roles and case.responsible_planner_user_id:
                        queue_notification(db, case_id=case.id, recipient_user_id=case.responsible_planner_user_id, type="case_overdue")
                    if "doctor" in rule.notify_roles and case.primary_doctor_user_id:
                        queue_notification(db, case_id=case.id, recipient_user_id=case.primary_doctor_user_id, type="case_overdue")
                    if "admin" in rule.notify_roles:
                        _notify_admins(db, case.id, "case_overdue")
                db.commit()

    return {"reminders_sent": reminders_sent, "cases_marked_overdue": cases_marked_overdue}

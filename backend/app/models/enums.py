"""Enums shared across models.

Kept deliberately small: anything that is clinical taxonomy (finding
categories, severities, checklist questions) is stored as free text / JSON in
the database instead, per ARCHITECTURE.md — only workflow/plumbing states are
real enums here.
"""
import enum


class Role(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    PLANNER = "planner"
    DOCTOR = "doctor"
    CONSULTANT = "consultant"


class CaseStatus(str, enum.Enum):
    NEW = "NEW"
    WAITING_ASSIGNMENT = "WAITING_ASSIGNMENT"
    ASSIGNED = "ASSIGNED"
    IMAGES_READY = "IMAGES_READY"
    ANALYSIS_IN_PROGRESS = "ANALYSIS_IN_PROGRESS"
    PLAN_IN_PROGRESS = "PLAN_IN_PROGRESS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    READY = "READY"
    CONSULTATION_COMPLETED = "CONSULTATION_COMPLETED"
    OVERDUE = "OVERDUE"


class Priority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ImageCategory(str, enum.Enum):
    EXTRAORAL = "extraoral"
    INTRAORAL = "intraoral"
    RADIOLOGY = "radiology"


class ImageSource(str, enum.Enum):
    CLINICCARDS = "cliniccards"
    UPLOAD = "upload"


class AnswerType(str, enum.Enum):
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    BOOLEAN = "boolean"
    TEXT = "text"
    MEASUREMENT = "measurement"


class ReviewDecision(str, enum.Enum):
    APPROVE = "approve"
    REVISION_REQUIRED = "revision_required"


class PresentationFormat(str, enum.Enum):
    PPTX = "pptx"
    PDF = "pdf"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class ReminderTriggerType(str, enum.Enum):
    ON_ASSIGNMENT = "on_assignment"
    BEFORE_CONSULTATION = "before_consultation"
    AFTER_DEADLINE = "after_deadline"


class SyncType(str, enum.Enum):
    POLL = "poll"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class SyncStatus(str, enum.Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


class AssignmentMode(str, enum.Enum):
    MANUAL = "manual"
    AUTO = "auto"


class AssignmentStrategy(str, enum.Enum):
    LEAST_WORKLOAD = "least_workload"
    ROUND_ROBIN = "round_robin"

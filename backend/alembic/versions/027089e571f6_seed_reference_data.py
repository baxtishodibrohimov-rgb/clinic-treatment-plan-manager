"""seed reference data

Revision ID: 027089e571f6
Revises: f5f15b2393d5
Create Date: 2026-09-07 04:51:05.524926

Seeds the reference/config data that should exist in every environment
(default image types per spec section 10, default reminder schedule per
section 7, the assignment-config singleton row) — as opposed to demo data
(fake patients/cases), which lives in app/seed.py and is meant to be run
only in development.
"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '027089e571f6'
down_revision: Union[str, None] = 'f5f15b2393d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

IMAGE_TYPES = [
    ("face_frontal", "Face frontal", "extraoral", True, 1),
    ("face_frontal_smile", "Face frontal smile", "extraoral", True, 2),
    ("face_profile_right", "Face profile right", "extraoral", True, 3),
    ("face_profile_left", "Face profile left", "extraoral", True, 4),
    ("face_three_quarter", "3/4 view", "extraoral", False, 5),
    ("intraoral_frontal", "Intraoral frontal", "intraoral", True, 6),
    ("intraoral_right_buccal", "Right buccal", "intraoral", True, 7),
    ("intraoral_left_buccal", "Left buccal", "intraoral", True, 8),
    ("intraoral_upper_occlusal", "Upper occlusal", "intraoral", True, 9),
    ("intraoral_lower_occlusal", "Lower occlusal", "intraoral", True, 10),
    ("opg_panoramic", "OPG / panoramic", "radiology", True, 11),
    ("lateral_cephalogram", "Lateral cephalogram", "radiology", True, 12),
]

REMINDER_RULES = [
    ("Case biriktirilganda", "on_assignment", None, ["planner"], 1),
    ("Konsultatsiyaga 24 soat qolganda", "before_consultation", 1440, ["planner"], 2),
    ("Konsultatsiyaga 12 soat qolganda", "before_consultation", 720, ["planner"], 3),
    ("Konsultatsiyaga 6 soat qolganda", "before_consultation", 360, ["planner"], 4),
    ("Konsultatsiyaga 2 soat qolganda", "before_consultation", 120, ["planner"], 5),
    ("Deadline o'tganda (OVERDUE)", "after_deadline", 0, ["planner", "admin", "doctor"], 6),
]

APP_SETTINGS = [
    ("second_consultation_appointment_type_codes", ["consultation_2", "2-konsultatsiya"]),
    ("default_deadline_hours_before_consultation", 24),
    ("presentation_clinic_name", "Clinic"),
    ("presentation_language", "uz"),
]


def upgrade() -> None:
    image_category_enum = postgresql.ENUM("extraoral", "intraoral", "radiology", name="image_category", create_type=False)
    image_types = sa.table(
        "image_types",
        sa.column("id", postgresql.UUID),
        sa.column("code", sa.String),
        sa.column("label", sa.String),
        sa.column("category", image_category_enum),
        sa.column("is_required", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        image_types,
        [
            {
                "id": uuid.uuid4(),
                "code": code,
                "label": label,
                "category": category,
                "is_required": required,
                "is_active": True,
                "sort_order": order,
            }
            for code, label, category, required, order in IMAGE_TYPES
        ],
    )

    reminder_trigger_enum = postgresql.ENUM(
        "on_assignment", "before_consultation", "after_deadline", name="reminder_trigger_type", create_type=False
    )
    reminder_rules = sa.table(
        "reminder_rules",
        sa.column("id", postgresql.UUID),
        sa.column("name", sa.String),
        sa.column("trigger_type", reminder_trigger_enum),
        sa.column("offset_minutes", sa.Integer),
        sa.column("notify_roles", sa.ARRAY(sa.String)),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        reminder_rules,
        [
            {
                "id": uuid.uuid4(),
                "name": name,
                "trigger_type": trigger,
                "offset_minutes": offset,
                "notify_roles": roles,
                "is_active": True,
                "sort_order": order,
            }
            for name, trigger, offset, roles, order in REMINDER_RULES
        ],
    )

    op.execute("INSERT INTO assignment_config (id, mode, strategy) VALUES (1, 'manual', 'least_workload')")

    app_settings = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.JSON),
    )
    op.bulk_insert(app_settings, [{"key": key, "value": value} for key, value in APP_SETTINGS])


def downgrade() -> None:
    op.execute("DELETE FROM app_settings")
    op.execute("DELETE FROM assignment_config")
    op.execute("DELETE FROM reminder_rules")
    op.execute("DELETE FROM image_types")

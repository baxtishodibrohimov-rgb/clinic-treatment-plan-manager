"""confirmed 13-step wizard questionnaire and image type reorder

Revision ID: a1b2c3d4e5f6
Revises: facc529edd2a
Create Date: 2026-09-16 12:00:00.000000

The clinic gave an exact, ordered 13-photo capture sequence and the exact
wording for all of its questions directly in chat, superseding the
970995590f0f seed (which was itself dictated but organized differently —
right/left profile shots for "tinch holat", no overjet/45deg/M-at-90 steps).

This migration:
  - adds the missing image types (overjet, face_45_smile,
    face_profile_90_rest/m/smile) and sets sort_order to match the
    confirmed sequence.
  - marks face_profile_right / face_profile_left / face_three_quarter /
    face_profile_smile as no longer required — they predate the confirmed
    sequence and aren't part of it (their profile-state distinction is now
    carried by the face_profile_90_* trio instead of left/right).
  - replaces analysis_templates entirely with the clinic's confirmed 22
    questions, one row per (image_type, question).
"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'facc529edd2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_IMAGE_TYPES = [
    # code, label, category, is_required, sort_order
    ("overjet", "Overjet", "intraoral", True, 4),
    ("face_45_smile", "45° — kulgan holat", "extraoral", True, 10),
    ("face_profile_90_rest", "Profil 90° — tinch holat", "extraoral", True, 11),
    ("face_profile_90_m", "Profil 90° — \"M\" holati", "extraoral", True, 12),
    ("face_profile_90_smile", "Profil 90° — kulgan holat", "extraoral", True, 13),
]

REORDER = [
    ("intraoral_frontal", 1),
    ("intraoral_right_buccal", 2),
    ("intraoral_left_buccal", 3),
    ("intraoral_upper_occlusal", 5),
    ("intraoral_lower_occlusal", 6),
    ("face_frontal", 7),
    ("face_frontal_m", 8),
    ("face_frontal_smile", 9),
]

DEPRECATED_CODES = ["face_profile_right", "face_profile_left", "face_three_quarter", "face_profile_smile"]

# (image_type_code, category, question, answer_type, options, sort_order)
TEMPLATES = [
    ("intraoral_frontal", "Frontal", "Pastki jag' markaziy chizig'i", "single_choice",
     ["Norma", "O'ngga siljigan", "Chapga siljigan"], 1),
    ("intraoral_frontal", "Frontal", "Prikus turi (old, vertikal)", "single_choice",
     ["Normal", "Ochiq", "Chuqur", "To'g'ri", "Teskari", "Kesishgan"], 2),
    ("intraoral_frontal", "Frontal", "Orqa prikus", "single_choice", ["Norma", "Kesishgan"], 3),

    ("intraoral_right_buccal", "Buccal", "Angle klassi, molyar (6-tish), o'ng", "single_choice",
     ["I", "II", "III"], 1),
    ("intraoral_right_buccal", "Buccal", "Angle klassi, klyk (3-tish), o'ng", "single_choice",
     ["I", "II", "III"], 2),

    ("intraoral_left_buccal", "Buccal", "Angle klassi, molyar (6-tish), chap", "single_choice",
     ["I", "II", "III"], 1),
    ("intraoral_left_buccal", "Buccal", "Angle klassi, klyk (3-tish), chap", "single_choice",
     ["I", "II", "III"], 2),

    ("overjet", "Overjet", "Overjet holati", "single_choice", ["Normal", "Ko'p", "Kam"], 1),

    ("intraoral_upper_occlusal", "Okklyuzion", "Joy yetishmasligi / qiyshiqlik darajasi", "text", [], 1),
    ("intraoral_lower_occlusal", "Okklyuzion", "Joy yetishmasligi / qiyshiqlik darajasi", "text", [], 1),

    ("face_frontal", "Profil", "Lablar holati", "single_choice", ["Tinch", "Majburiy yopilgan"], 1),
    ("face_frontal", "Profil", "Pastki jag' holati (simmetriya)", "single_choice", ["Simmetrik", "Asimmetrik"], 2),
    ("face_frontal", "Profil", "Agar asimmetrik bo'lsa — tomonini yozing", "text", [], 3),

    ("face_frontal_m", "Profil", "Yuqori kurak tishlarning ko'rinish darajasi", "text", [], 1),

    ("face_frontal_smile", "Tabassum", "Ekspozitsiya darajasi", "single_choice", ["Normal", "Ko'p", "Kam"], 1),
    ("face_frontal_smile", "Tabassum", "Milk holati (gummy smile)", "single_choice", ["Yo'q", "Kam", "Ko'p"], 2),
    ("face_frontal_smile", "Tabassum", "Markaziy chiziq (yuzga nisbatan)", "single_choice",
     ["Norma", "O'ngga siljigan", "Chapga siljigan"], 3),

    ("face_45_smile", "Tabassum", "Arka (smile arc) holati", "single_choice", ["Norma", "Ko'p", "Kam"], 1),

    ("face_profile_90_rest", "Profil 90°", "Profil turi", "single_choice", ["Protrusion", "Retrusion"], 1),
    ("face_profile_90_rest", "Profil 90°", "Klass moyilligi", "single_choice",
     ["Norma", "2-klassga moyillik", "3-klassga moyillik"], 2),

    ("face_profile_90_m", "Profil 90°", "Tishlar holati", "single_choice", ["Norma", "Protrusiya", "Retrusiya"], 1),

    ("face_profile_90_smile", "Profil 90°", "Tishlar holati", "single_choice", ["Norma", "Protrusiya", "Retrusiya"], 1),
]


def upgrade() -> None:
    conn = op.get_bind()
    image_category_enum = postgresql.ENUM("extraoral", "intraoral", "radiology", name="image_category", create_type=False)
    image_types_t = sa.table(
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
        image_types_t,
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
            for code, label, category, required, order in NEW_IMAGE_TYPES
        ],
    )

    for code, order in REORDER:
        conn.execute(sa.text("UPDATE image_types SET sort_order = :order WHERE code = :code"), {"order": order, "code": code})

    for code in DEPRECATED_CODES:
        conn.execute(
            sa.text("UPDATE image_types SET is_required = false, sort_order = sort_order + 100 WHERE code = :code"),
            {"code": code},
        )

    conn.execute(sa.text("DELETE FROM analysis_templates"))

    code_to_id: dict[str, uuid.UUID] = {
        row[0]: row[1] for row in conn.execute(sa.text("SELECT code, id FROM image_types")).fetchall()
    }

    answer_type_enum = postgresql.ENUM(
        "single_choice", "multi_choice", "boolean", "text", "measurement", name="answer_type", create_type=False
    )
    analysis_templates_t = sa.table(
        "analysis_templates",
        sa.column("id", postgresql.UUID),
        sa.column("template_name", sa.String),
        sa.column("image_type_id", postgresql.UUID),
        sa.column("category", sa.String),
        sa.column("question", sa.Text),
        sa.column("answer_type", answer_type_enum),
        sa.column("options", postgresql.JSONB),
        sa.column("measurement_required", sa.Boolean),
        sa.column("annotation_required", sa.Boolean),
        sa.column("active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        analysis_templates_t,
        [
            {
                "id": uuid.uuid4(),
                "template_name": f"{category}: {question}",
                "image_type_id": code_to_id[image_type_code],
                "category": category,
                "question": question,
                "answer_type": answer_type,
                "options": options,
                "measurement_required": False,
                "annotation_required": False,
                "active": True,
                "sort_order": order,
            }
            for image_type_code, category, question, answer_type, options, order in TEMPLATES
        ],
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM analysis_templates"))
    for code in DEPRECATED_CODES:
        conn.execute(
            sa.text("UPDATE image_types SET is_required = true, sort_order = sort_order - 100 WHERE code = :code"),
            {"code": code},
        )
    conn.execute(sa.text(f"DELETE FROM image_types WHERE code IN ({', '.join(repr(c) for c, *_ in NEW_IMAGE_TYPES)})"))

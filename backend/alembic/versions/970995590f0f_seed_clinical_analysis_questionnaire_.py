"""seed clinical analysis questionnaire from clinic manual

Revision ID: 970995590f0f
Revises: 3938cb64131c
Create Date: 2026-09-16 06:11:29.117242

Adds two extraoral image types the clinic's photo protocol uses that
weren't in the original seed ("M" position, profile-while-smiling), then
seeds the real Phase 5 analysis questionnaire — dictated by the clinic
owner, not invented — as AnalysisTemplate rows grouped by image type.

X-ray (OPG/lateral ceph) questions and the interactive tooth chart are
deliberately NOT part of this seed: the X-ray questionnaire wasn't
provided yet, and the tooth chart's 32 positions are generated on demand
by app/services/analysis_service.py, not seeded as template rows.
"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '970995590f0f'
down_revision: Union[str, None] = '3938cb64131c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_IMAGE_TYPES = [
    # code, label, category, is_required, sort_order
    ("face_frontal_m", "Frontal — \"M\" holati", "extraoral", True, 13),
    ("face_profile_smile", "Profil — kulgan holatda", "extraoral", True, 14),
]

# Each entry: (image_type_code | None, category, question, answer_type, options, sort_order)
# image_type_code=None means the question isn't tied to one specific photo
# (e.g. crowding, judged across the whole occlusal arch).
TEMPLATES = [
    # --- Og'iz ichi, old tomondan ---
    ("intraoral_frontal", "intraoral", "Pastki jag' markaziy chizig'i", "single_choice",
     ["Normal", "O'ngga siljigan", "Chapga siljigan"], 1),
    ("intraoral_frontal", "intraoral", "Pastki jag' qochganmi?", "boolean", [], 2),
    ("intraoral_frontal", "intraoral", "Prikus turi (old tomondan)", "single_choice",
     ["Normal", "Ochiq prikus", "Chuqur (yopiq) prikus", "To'g'ri prikus", "Teskari prikus", "Kesishgan prikus"], 3),
    ("intraoral_frontal", "intraoral", "Orqa tishlar prikusi", "single_choice", ["Normal", "Kesishgan"], 4),
    ("intraoral_frontal", "intraoral", "Qo'shimcha izoh", "text", [], 5),

    # --- Og'iz ichi, yon tomon (Angle klassi) ---
    ("intraoral_right_buccal", "intraoral", "6-tish (molyar) Angle klassi — o'ng tomon", "single_choice",
     ["I klass", "II klass", "III klass"], 1),
    ("intraoral_right_buccal", "intraoral", "3-tish (klyk) Angle klassi — o'ng tomon", "single_choice",
     ["I klass", "II klass", "III klass"], 2),
    ("intraoral_right_buccal", "intraoral", "Qo'shimcha izoh", "text", [], 3),

    ("intraoral_left_buccal", "intraoral", "6-tish (molyar) Angle klassi — chap tomon", "single_choice",
     ["I klass", "II klass", "III klass"], 1),
    ("intraoral_left_buccal", "intraoral", "3-tish (klyk) Angle klassi — chap tomon", "single_choice",
     ["I klass", "II klass", "III klass"], 2),
    ("intraoral_left_buccal", "intraoral", "Qo'shimcha izoh", "text", [], 3),

    # --- Okklyuzion (butun qatorga tegishli, bitta rasmga bog'lanmagan) ---
    (None, "intraoral", "Joy yetishmasligi va qiyshiqlik darajasi", "text", [], 1),
    (None, "intraoral", "Qo'shimcha izoh", "text", [], 2),

    # --- Profil, tinch holat ---
    ("face_frontal", "extraoral", "Lablar holati", "single_choice", ["Tinch", "Majburiy yopilgan"], 1),
    ("face_frontal", "extraoral", "Pastki jag' (yuzga nisbatan)", "single_choice", ["Simmetrik", "Asimmetrik"], 2),
    ("face_frontal", "extraoral", "Asimmetriya tavsifi (mavjud bo'lsa)", "text", [], 3),
    ("face_frontal", "extraoral", "Qo'shimcha izoh", "text", [], 4),

    # --- "M" holati ---
    ("face_frontal_m", "extraoral", "Yuqori tishlar ko'rinish darajasi", "single_choice",
     ["Normal", "Ko'p", "Kam"], 1),
    ("face_frontal_m", "extraoral", "Qo'shimcha izoh", "text", [], 2),

    # --- Kulgan holat ---
    ("face_frontal_smile", "extraoral", "Ko'rinadigan tishlar", "single_choice",
     ["Faqat yuqori jag'", "Yuqori va pastki jag'"], 1),
    ("face_frontal_smile", "extraoral", "Ekspozitsiya (tish-milk ko'rinishi)", "single_choice",
     ["Normal", "Ko'p", "Kam"], 2),
    ("face_frontal_smile", "extraoral", "Markaziy chiziq (yuzga nisbatan)", "single_choice",
     ["Norma", "O'ng tomonga siljigan", "Chap tomonga siljigan"], 3),
    ("face_frontal_smile", "extraoral", "Qo'shimcha izoh", "text", [], 4),

    # --- Profil (90 gradus) ---
    ("face_profile_right", "extraoral", "Profil turi", "single_choice",
     ["Qavariq", "Botiq", "Protrusion", "Retrusion"], 1),
    ("face_profile_right", "extraoral", "II klassga moyillik (tinch holatda)", "boolean", [], 2),
    ("face_profile_right", "extraoral", "Moyillik tavsifi (mavjud bo'lsa)", "text", [], 3),
    ("face_profile_right", "extraoral", "Qo'shimcha izoh", "text", [], 4),

    ("face_profile_left", "extraoral", "Profil turi", "single_choice",
     ["Qavariq", "Botiq", "Protrusion", "Retrusion"], 1),
    ("face_profile_left", "extraoral", "II klassga moyillik (tinch holatda)", "boolean", [], 2),
    ("face_profile_left", "extraoral", "Moyillik tavsifi (mavjud bo'lsa)", "text", [], 3),
    ("face_profile_left", "extraoral", "Qo'shimcha izoh", "text", [], 4),

    # --- Profil, kulgan holatda ---
    ("face_profile_smile", "extraoral", "Tishlar holati", "single_choice",
     ["Norma", "Protrusiya", "Retrusiya"], 1),
    ("face_profile_smile", "extraoral", "Qo'shimcha izoh", "text", [], 2),
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
                "template_name": "Klinik tahlil (og'iz ichi va profil)",
                "image_type_id": code_to_id[image_type_code] if image_type_code else None,
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
    op.execute("DELETE FROM analysis_templates WHERE template_name = 'Klinik tahlil (og''iz ichi va profil)'")
    op.execute(f"DELETE FROM image_types WHERE code IN ({', '.join(repr(c) for c, *_ in NEW_IMAGE_TYPES)})")

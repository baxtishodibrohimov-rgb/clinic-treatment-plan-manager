"""clarify smile-photo midline question as upper jaw

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-16 13:00:00.000000

The clinic wants the two midline questions asked back-to-back as one
clinical thought: upper-jaw midline (judged against the face, on the
frontal-smile photo) immediately followed by lower-jaw midline (judged
intraorally, on the intraoral-frontal photo) — see the wizard's
WIZARD_FLOW in frontend/src/app/cases/[id]/analysis/page.tsx for the
sequencing. The two questions already existed as two separate template
rows tied to their own photos; this migration only renames the
frontal-smile one to say "upper jaw" explicitly, since it's no longer a
generic "midline" question sitting on its own — it's now paired with the
"Pastki jag' markaziy chizig'i" question on the intraoral-frontal photo.
No new rows, no image_type change.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_QUESTION = "Markaziy chiziq (yuzga nisbatan)"
NEW_QUESTION = "Tepa jag' markaziy chizig'i (yuzga nisbatan)"
OLD_TEMPLATE_NAME = "Tabassum: Markaziy chiziq (yuzga nisbatan)"
NEW_TEMPLATE_NAME = "Tabassum: Tepa jag' markaziy chizig'i (yuzga nisbatan)"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE analysis_templates SET question = :new_q, template_name = :new_name WHERE question = :old_q"),
        {"new_q": NEW_QUESTION, "new_name": NEW_TEMPLATE_NAME, "old_q": OLD_QUESTION},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE analysis_templates SET question = :old_q, template_name = :old_name WHERE question = :new_q"),
        {"old_q": OLD_QUESTION, "old_name": OLD_TEMPLATE_NAME, "new_q": NEW_QUESTION},
    )

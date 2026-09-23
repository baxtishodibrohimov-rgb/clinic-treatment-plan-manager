"""add cached image thumbnails

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clinical_images", sa.Column("thumbnail_data", sa.LargeBinary(), nullable=True))
    op.add_column("clinical_images", sa.Column("thumbnail_mime_type", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("clinical_images", "thumbnail_mime_type")
    op.drop_column("clinical_images", "thumbnail_data")

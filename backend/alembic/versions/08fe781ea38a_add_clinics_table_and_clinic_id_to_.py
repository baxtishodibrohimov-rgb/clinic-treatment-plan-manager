"""add clinics table and clinic_id to users and cases

Revision ID: 08fe781ea38a
Revises: 027089e571f6
Create Date: 2026-09-07 13:09:56.627828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08fe781ea38a'
down_revision: Union[str, None] = '027089e571f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('clinics',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('cliniccards_branch_code', sa.String(length=255), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('cases', sa.Column('clinic_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_cases_clinic_id'), 'cases', ['clinic_id'], unique=False)
    op.create_foreign_key('fk_cases_clinic_id_clinics', 'cases', 'clinics', ['clinic_id'], ['id'], ondelete='SET NULL')
    op.add_column('users', sa.Column('clinic_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_users_clinic_id'), 'users', ['clinic_id'], unique=False)
    op.create_foreign_key('fk_users_clinic_id_clinics', 'users', 'clinics', ['clinic_id'], ['id'], ondelete='SET NULL')

    # Data backfill: every pre-existing user/case predates the multi-clinic
    # feature, so they all belong together in one clinic. Real deployments
    # rename this (or add more clinics) from Settings > Clinics afterward.
    # SUPER_ADMIN users are left with clinic_id = NULL (they see everything).
    conn = op.get_bind()
    clinic_id = conn.execute(sa.text(
        "INSERT INTO clinics (id, name, is_active, is_default, created_at, updated_at) "
        "VALUES (gen_random_uuid(), 'Bosh klinika', true, true, now(), now()) RETURNING id"
    )).scalar_one()
    conn.execute(sa.text(
        "UPDATE users SET clinic_id = :clinic_id WHERE id NOT IN "
        "(SELECT user_id FROM user_roles WHERE role = 'super_admin')"
    ), {"clinic_id": clinic_id})
    conn.execute(sa.text("UPDATE cases SET clinic_id = :clinic_id"), {"clinic_id": clinic_id})


def downgrade() -> None:
    op.drop_constraint('fk_users_clinic_id_clinics', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_clinic_id'), table_name='users')
    op.drop_column('users', 'clinic_id')
    op.drop_constraint('fk_cases_clinic_id_clinics', 'cases', type_='foreignkey')
    op.drop_index(op.f('ix_cases_clinic_id'), table_name='cases')
    op.drop_column('cases', 'clinic_id')
    op.drop_table('clinics')

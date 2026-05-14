"""Add required_models to workers

Revision ID: 005
Revises: 004
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('workers', sa.Column('required_models', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('workers', 'required_models')

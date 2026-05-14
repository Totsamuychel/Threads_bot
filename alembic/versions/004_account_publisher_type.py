"""Add publisher_type to accounts

Revision ID: 004
Revises: 003
Create Date: 2026-05-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('accounts', sa.Column('publisher_type', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('accounts', 'publisher_type')

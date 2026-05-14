"""Add threads OAuth fields to accounts

Revision ID: 002
Revises: 001
Create Date: 2026-05-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('accounts', sa.Column('threads_user_id', sa.String(length=100), nullable=True))
    op.add_column('accounts', sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True))
    # Widen api_token to accommodate Fernet-encrypted values
    op.alter_column('accounts', 'api_token', type_=sa.String(length=700), existing_nullable=True)


def downgrade() -> None:
    op.drop_column('accounts', 'token_expires_at')
    op.drop_column('accounts', 'threads_user_id')
    op.alter_column('accounts', 'api_token', type_=sa.String(length=500), existing_nullable=True)

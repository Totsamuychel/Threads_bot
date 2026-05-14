"""Add social actions table and account social config columns

Revision ID: 003
Revises: 002
Create Date: 2026-05-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Social config columns on accounts
    op.add_column('accounts', sa.Column('social_actions_enabled', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('accounts', sa.Column('likes_per_day', sa.Integer(), nullable=True, server_default='20'))
    op.add_column('accounts', sa.Column('replies_per_day', sa.Integer(), nullable=True, server_default='5'))
    op.add_column('accounts', sa.Column('follows_per_day', sa.Integer(), nullable=True, server_default='10'))

    # Social actions log table
    op.create_table(
        'social_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=20), nullable=False),
        sa.Column('target_post_id', sa.String(length=200), nullable=True),
        sa.Column('target_user_id', sa.String(length=200), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_social_actions_id', 'social_actions', ['id'])
    op.create_index('ix_social_actions_account_id', 'social_actions', ['account_id'])
    op.create_index('ix_social_actions_action_type', 'social_actions', ['action_type'])
    op.create_index('ix_social_actions_created_at', 'social_actions', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_social_actions_created_at', 'social_actions')
    op.drop_index('ix_social_actions_action_type', 'social_actions')
    op.drop_index('ix_social_actions_account_id', 'social_actions')
    op.drop_index('ix_social_actions_id', 'social_actions')
    op.drop_table('social_actions')

    op.drop_column('accounts', 'follows_per_day')
    op.drop_column('accounts', 'replies_per_day')
    op.drop_column('accounts', 'likes_per_day')
    op.drop_column('accounts', 'social_actions_enabled')

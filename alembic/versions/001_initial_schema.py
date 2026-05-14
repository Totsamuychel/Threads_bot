"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create accounts table
    op.create_table('accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=True),
        sa.Column('api_token', sa.String(length=500), nullable=True),
        sa.Column('credentials_env_key', sa.String(length=100), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True),
        sa.Column('schedule_type', sa.String(length=20), nullable=True),
        sa.Column('schedule_config', sa.JSON(), nullable=True),
        sa.Column('max_posts_per_day', sa.Integer(), nullable=True),
        sa.Column('topics', sa.JSON(), nullable=True),
        sa.Column('tone', sa.Text(), nullable=True),
        sa.Column('target_audience', sa.Text(), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('base_hashtags', sa.JSON(), nullable=True),
        sa.Column('auto_generate_hashtags', sa.Boolean(), nullable=True),
        sa.Column('max_hashtags', sa.Integer(), nullable=True),
        sa.Column('min_length', sa.Integer(), nullable=True),
        sa.Column('max_length', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_accounts_id'), 'accounts', ['id'], unique=False)
    op.create_index(op.f('ix_accounts_username'), 'accounts', ['username'], unique=True)

    # Create content_plans table
    op.create_table('content_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('topic', sa.String(length=200), nullable=False),
        sa.Column('specific_idea', sa.Text(), nullable=True),
        sa.Column('scheduled_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.Enum('PLANNED', 'GENERATING', 'GENERATED', 'SCHEDULED', 'PUBLISHING', 'POSTED', 'FAILED', 'CANCELLED', name='poststatus'), nullable=True),
        sa.Column('llm_model', sa.String(length=100), nullable=True),
        sa.Column('llm_temperature', sa.String(length=10), nullable=True),
        sa.Column('llm_max_tokens', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_plans_id'), 'content_plans', ['id'], unique=False)
    op.create_index(op.f('ix_content_plans_scheduled_time'), 'content_plans', ['scheduled_time'], unique=False)
    op.create_index(op.f('ix_content_plans_status'), 'content_plans', ['status'], unique=False)

    # Create posts table
    op.create_table('posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('content_plan_id', sa.Integer(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('hashtags', sa.JSON(), nullable=True),
        sa.Column('media_urls', sa.JSON(), nullable=True),
        sa.Column('llm_prompt', sa.Text(), nullable=True),
        sa.Column('llm_system_prompt', sa.Text(), nullable=True),
        sa.Column('llm_raw_response', sa.Text(), nullable=True),
        sa.Column('llm_model_used', sa.String(length=100), nullable=True),
        sa.Column('generation_time_seconds', sa.Integer(), nullable=True),
        sa.Column('scheduled_time', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('threads_post_id', sa.String(length=200), nullable=True),
        sa.Column('threads_post_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.Enum('PLANNED', 'GENERATING', 'GENERATED', 'SCHEDULED', 'PUBLISHING', 'POSTED', 'FAILED', 'CANCELLED', name='poststatus'), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['content_plan_id'], ['content_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_posts_id'), 'posts', ['id'], unique=False)
    op.create_index(op.f('ix_posts_published_at'), 'posts', ['published_at'], unique=False)
    op.create_index(op.f('ix_posts_scheduled_time'), 'posts', ['scheduled_time'], unique=False)
    op.create_index(op.f('ix_posts_status'), 'posts', ['status'], unique=False)

    # Create activity_logs table
    op.create_table('activity_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_category', sa.String(length=50), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=True),
        sa.Column('content_plan_id', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activity_logs_created_at'), 'activity_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_activity_logs_event_category'), 'activity_logs', ['event_category'], unique=False)
    op.create_index(op.f('ix_activity_logs_event_type'), 'activity_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_activity_logs_id'), 'activity_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_activity_logs_id'), table_name='activity_logs')
    op.drop_index(op.f('ix_activity_logs_event_type'), table_name='activity_logs')
    op.drop_index(op.f('ix_activity_logs_event_category'), table_name='activity_logs')
    op.drop_index(op.f('ix_activity_logs_created_at'), table_name='activity_logs')
    op.drop_table('activity_logs')
    
    op.drop_index(op.f('ix_posts_status'), table_name='posts')
    op.drop_index(op.f('ix_posts_scheduled_time'), table_name='posts')
    op.drop_index(op.f('ix_posts_published_at'), table_name='posts')
    op.drop_index(op.f('ix_posts_id'), table_name='posts')
    op.drop_table('posts')
    
    op.drop_index(op.f('ix_content_plans_status'), table_name='content_plans')
    op.drop_index(op.f('ix_content_plans_scheduled_time'), table_name='content_plans')
    op.drop_index(op.f('ix_content_plans_id'), table_name='content_plans')
    op.drop_table('content_plans')
    
    op.drop_index(op.f('ix_accounts_username'), table_name='accounts')
    op.drop_index(op.f('ix_accounts_id'), table_name='accounts')
    op.drop_table('accounts')
    
    # Drop enum type
    sa.Enum(name='poststatus').drop(op.get_bind(), checkfirst=True)

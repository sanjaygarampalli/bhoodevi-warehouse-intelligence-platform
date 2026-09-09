"""Add assigned Lead/Deal follow-up tasks.

Revision ID: k6c7d8e9f0a1
Revises: j5b6c7d8e9f0
"""
from alembic import op
import sqlalchemy as sa

revision = "k6c7d8e9f0a1"
down_revision = "j5b6c7d8e9f0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "follow_up_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("deal_id", sa.Integer(), sa.ForeignKey("deals.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("task_type", sa.String(30), server_default="OTHER", nullable=False),
        sa.Column("priority", sa.String(10), server_default="MEDIUM", nullable=False),
        sa.Column("status", sa.String(20), server_default="OPEN", nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("recommendation_key", sa.String(50), nullable=True),
        sa.Column("recommendation_context", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("task_type IN ('CALL','EMAIL','LINKEDIN','WHATSAPP','MEETING','PROPOSAL_FOLLOWUP','REVIEW','ADMIN','OTHER')", name="ck_follow_up_tasks__type"),
        sa.CheckConstraint("priority IN ('LOW','MEDIUM','HIGH','URGENT')", name="ck_follow_up_tasks__priority"),
        sa.CheckConstraint("status IN ('OPEN','IN_PROGRESS','COMPLETED','CANCELLED')", name="ck_follow_up_tasks__status"),
        sa.CheckConstraint(
            "(status = 'COMPLETED' AND completed_at IS NOT NULL AND cancelled_at IS NULL) OR "
            "(status = 'CANCELLED' AND cancelled_at IS NOT NULL AND completed_at IS NULL) OR "
            "(status IN ('OPEN','IN_PROGRESS') AND completed_at IS NULL AND cancelled_at IS NULL)",
            name="ck_follow_up_tasks__closure",
        ),
        sa.CheckConstraint("length(trim(subject)) > 0", name="ck_follow_up_tasks__subject"),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_follow_up_tasks__assigned_to_user_id__status__due_at", "follow_up_tasks", ["assigned_to_user_id", "status", "due_at"])
    op.create_index("ix_follow_up_tasks__lead_id__status", "follow_up_tasks", ["lead_id", "status"])
    op.create_index("ix_follow_up_tasks__due_at", "follow_up_tasks", ["due_at"])
    op.create_index("ix_follow_up_tasks__deal_id", "follow_up_tasks", ["deal_id"])
    op.create_index("uq_follow_up_tasks__active_recommendation", "follow_up_tasks", ["lead_id", "recommendation_key"], unique=True,
                    sqlite_where=sa.text("status IN ('OPEN','IN_PROGRESS') AND recommendation_key IS NOT NULL"),
                    postgresql_where=sa.text("status IN ('OPEN','IN_PROGRESS') AND recommendation_key IS NOT NULL"))


def downgrade():
    # Explicit rollback is destructive to task history; parent domains are retained.
    op.drop_table("follow_up_tasks")
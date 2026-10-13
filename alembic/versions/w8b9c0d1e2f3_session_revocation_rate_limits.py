"""Add durable credential revocation and shared request quotas."""
from alembic import op
import sqlalchemy as sa

revision = "w8b9c0d1e2f3"
down_revision = "v7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    op.create_table("rate_limit_buckets", sa.Column("key", sa.String(64), primary_key=True),
                    sa.Column("count", sa.Integer(), nullable=False),
                    sa.Column("expires_at", sa.BigInteger(), nullable=False))
    op.create_index("ix_rate_limit_buckets_expires_at", "rate_limit_buckets", ["expires_at"])


def downgrade():
    op.drop_table("rate_limit_buckets")
    op.drop_column("users", "token_version")

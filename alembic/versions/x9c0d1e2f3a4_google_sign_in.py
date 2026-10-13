"""Optional Google identity linking and single-use sign-in challenges."""
from alembic import op
import sqlalchemy as sa

revision = "x9c0d1e2f3a4"
down_revision = "w8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("google_subject", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_users_google_subject", "users", ["google_subject"])
    op.create_table("google_login_challenges",
                    sa.Column("nonce_hash", sa.String(64), primary_key=True),
                    sa.Column("expires_at", sa.BigInteger(), nullable=False))
    op.create_index("ix_google_login_challenges_expires_at", "google_login_challenges", ["expires_at"])


def downgrade():
    op.drop_table("google_login_challenges")
    op.drop_constraint("uq_users_google_subject", "users", type_="unique")
    op.drop_column("users", "google_subject")

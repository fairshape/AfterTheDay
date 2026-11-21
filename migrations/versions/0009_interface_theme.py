"""Remember the interface theme independently of saved scenes."""
from alembic import op
import sqlalchemy as sa

revision = "0009_interface_theme"
down_revision = "0008_film_sources"


def upgrade():
    op.add_column("user_preferences", sa.Column("theme", sa.String(8), nullable=False, server_default="paper"))


def downgrade():
    op.drop_column("user_preferences", "theme")

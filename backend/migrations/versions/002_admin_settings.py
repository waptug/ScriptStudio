"""Persist workflow configuration and encrypted provider credentials."""
from alembic import op
import sqlalchemy as sa

revision = '002_admin_settings'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('app_settings', sa.Column('key', sa.String(), primary_key=True),
                    sa.Column('value', sa.Text(), nullable=False))


def downgrade():
    op.drop_table('app_settings')

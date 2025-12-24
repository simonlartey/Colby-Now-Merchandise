"""merge heads

Revision ID: 84d22cc01cf3
Revises: 1341ad5c25ac, 4c0695acc2b0
Create Date: 2025-12-11 10:07:38.378079

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "84d22cc01cf3"
down_revision = ("1341ad5c25ac", "4c0695acc2b0")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass

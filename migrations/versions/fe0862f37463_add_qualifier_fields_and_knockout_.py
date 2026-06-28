"""add_qualifier_fields_and_knockout_matches

Revision ID: fe0862f37463
Revises: c4d5e6f7a8b9
Create Date: 2026-06-28 04:41:45.433719

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fe0862f37463'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.add_column(sa.Column('advancing_team', sa.String(length=50), nullable=True))

    with op.batch_alter_table('predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('predicted_qualifier', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('predictions', schema=None) as batch_op:
        batch_op.drop_column('predicted_qualifier')

    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_column('advancing_team')

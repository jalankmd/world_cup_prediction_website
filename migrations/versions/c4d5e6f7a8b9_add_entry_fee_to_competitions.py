"""add entry_fee to competitions

Revision ID: c4d5e6f7a8b9
Revises: b3e4f5a6c7d8
Create Date: 2026-06-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c4d5e6f7a8b9'
down_revision = 'b3e4f5a6c7d8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('competitions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('entry_fee', sa.Float(), nullable=False, server_default='0.0')
        )


def downgrade():
    with op.batch_alter_table('competitions', schema=None) as batch_op:
        batch_op.drop_column('entry_fee')

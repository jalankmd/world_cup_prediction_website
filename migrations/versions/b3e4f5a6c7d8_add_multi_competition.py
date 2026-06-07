"""add multi-competition support

Revision ID: b3e4f5a6c7d8
Revises: 7872bbd8d6be
Create Date: 2026-06-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b3e4f5a6c7d8'
down_revision = '7872bbd8d6be'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create user_competitions M2M table
    op.create_table(
        'user_competitions',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('competition_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['competition_id'], ['competitions.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('user_id', 'competition_id')
    )

    # 2. Populate user_competitions from existing users.competition_id
    op.execute("""
        INSERT INTO user_competitions (user_id, competition_id)
        SELECT id, competition_id FROM users WHERE competition_id IS NOT NULL
    """)

    # 3. predictions — add competition_id, replace unique constraint
    with op.batch_alter_table('predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('competition_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_pred_competition', 'competitions', ['competition_id'], ['id'])
        batch_op.drop_constraint('unique_user_match', type_='unique')
        batch_op.create_unique_constraint('unique_user_match_comp', ['user_id', 'match_id', 'competition_id'])

    op.execute("""
        UPDATE predictions SET competition_id = (
            SELECT competition_id FROM users WHERE users.id = predictions.user_id
        )
    """)

    # 4. odds_predictions — add competition_id, replace unique constraint
    with op.batch_alter_table('odds_predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('competition_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_odds_competition', 'competitions', ['competition_id'], ['id'])
        batch_op.drop_constraint('unique_user_match_odds', type_='unique')
        batch_op.create_unique_constraint('unique_user_match_comp_odds', ['user_id', 'match_id', 'competition_id'])

    op.execute("""
        UPDATE odds_predictions SET competition_id = (
            SELECT competition_id FROM users WHERE users.id = odds_predictions.user_id
        )
    """)

    # 5. group_qualifier_predictions — add competition_id, replace unique constraint
    with op.batch_alter_table('group_qualifier_predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('competition_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_gqp_competition', 'competitions', ['competition_id'], ['id'])
        batch_op.drop_constraint('unique_user_group_pick', type_='unique')
        batch_op.create_unique_constraint('unique_user_group_pick_comp', ['user_id', 'group_name', 'competition_id'])

    op.execute("""
        UPDATE group_qualifier_predictions SET competition_id = (
            SELECT competition_id FROM users WHERE users.id = group_qualifier_predictions.user_id
        )
    """)

    # 6. podium_predictions — add competition_id, remove old unique on user_id, add new compound unique
    # batch_alter_table recreates the table in SQLite, dropping the inline unique on user_id
    with op.batch_alter_table('podium_predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('competition_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_podium_competition', 'competitions', ['competition_id'], ['id'])
        # Remove the old column-level unique on user_id by altering it to non-unique
        batch_op.alter_column('user_id', existing_type=sa.Integer(), existing_nullable=False, unique=False)
        batch_op.create_unique_constraint('unique_user_comp_podium', ['user_id', 'competition_id'])

    op.execute("""
        UPDATE podium_predictions SET competition_id = (
            SELECT competition_id FROM users WHERE users.id = podium_predictions.user_id
        )
    """)


def downgrade():
    # Remove competition_id from prediction tables and restore old constraints
    with op.batch_alter_table('podium_predictions', schema=None) as batch_op:
        batch_op.drop_constraint('unique_user_comp_podium', type_='unique')
        batch_op.alter_column('user_id', existing_type=sa.Integer(), existing_nullable=False, unique=True)
        batch_op.drop_column('competition_id')

    with op.batch_alter_table('group_qualifier_predictions', schema=None) as batch_op:
        batch_op.drop_constraint('unique_user_group_pick_comp', type_='unique')
        batch_op.create_unique_constraint('unique_user_group_pick', ['user_id', 'group_name'])
        batch_op.drop_column('competition_id')

    with op.batch_alter_table('odds_predictions', schema=None) as batch_op:
        batch_op.drop_constraint('unique_user_match_comp_odds', type_='unique')
        batch_op.create_unique_constraint('unique_user_match_odds', ['user_id', 'match_id'])
        batch_op.drop_column('competition_id')

    with op.batch_alter_table('predictions', schema=None) as batch_op:
        batch_op.drop_constraint('unique_user_match_comp', type_='unique')
        batch_op.create_unique_constraint('unique_user_match', ['user_id', 'match_id'])
        batch_op.drop_column('competition_id')

    op.drop_table('user_competitions')

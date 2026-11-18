"""Reuse board aggregate tables for the manual; preserve every legacy value."""
from alembic import op
import sqlalchemy as sa

revision = 'd19c285da6eb'
down_revision = 'c08b174c95da'
branch_labels = depends_on = None


def upgrade():
    op.add_column('trivial_board_matches', sa.Column('manual_state', sa.JSON(), nullable=True))
    op.add_column('trivial_board_matches', sa.Column('subject_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_trivial_match_subject', 'trivial_board_matches', 'subjects', ['subject_id'], ['id'])
    op.create_index('ix_trivial_board_matches_subject_id', 'trivial_board_matches', ['subject_id'])
    # The old migration used anonymous checks; inspect their actual DB names.
    checks = sa.inspect(op.get_bind()).get_check_constraints('trivial_board_participants')
    bounds = [c for c in checks if 'slot' in c['sqltext'] and 'position' in c['sqltext']]
    if len(bounds) != 1 or not bounds[0]['name']:
        raise RuntimeError('Cannot identify the existing board participant bounds')
    op.drop_constraint(bounds[0]['name'], 'trivial_board_participants', type_='check')
    for name, type_ in [('position', sa.Integer()), ('phase', sa.String(24)), ('skip_next_own_turn', sa.Boolean())]:
        op.alter_column('trivial_board_participants', name, existing_type=type_, nullable=True)
    op.create_check_constraint('ck_trivial_participant_bounds', 'trivial_board_participants',
                               'slot BETWEEN 1 AND 6 AND (position IS NULL OR position BETWEEN 1 AND 140)')
    op.create_check_constraint('ck_trivial_participant_state_shape', 'trivial_board_participants',
        '(position IS NULL AND phase IS NULL AND skip_next_own_turn IS NULL) OR '
        '(position IS NOT NULL AND phase IS NOT NULL AND skip_next_own_turn IS NOT NULL)')


def downgrade():
    connection = op.get_bind()
    if (connection.scalar(sa.text('SELECT count(*) FROM trivial_board_matches WHERE manual_state IS NOT NULL OR subject_id IS NOT NULL'))
            or connection.scalar(sa.text('SELECT count(*) FROM trivial_board_participants WHERE position IS NULL OR slot > 4'))):
        raise RuntimeError('Cannot discard manual InmunoQuest state')
    op.drop_constraint('ck_trivial_participant_state_shape', 'trivial_board_participants', type_='check')
    op.drop_constraint('ck_trivial_participant_bounds', 'trivial_board_participants', type_='check')
    op.create_check_constraint('trivial_board_participants_check', 'trivial_board_participants',
                               'slot BETWEEN 1 AND 4 AND position BETWEEN 1 AND 140')
    for name, type_ in [('position', sa.Integer()), ('phase', sa.String(24)), ('skip_next_own_turn', sa.Boolean())]:
        op.alter_column('trivial_board_participants', name, existing_type=type_, nullable=False)
    op.drop_index('ix_trivial_board_matches_subject_id', table_name='trivial_board_matches')
    op.drop_constraint('fk_trivial_match_subject', 'trivial_board_matches', type_='foreignkey')
    op.drop_column('trivial_board_matches', 'subject_id')
    op.drop_column('trivial_board_matches', 'manual_state')

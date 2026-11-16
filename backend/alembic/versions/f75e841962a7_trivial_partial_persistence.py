"""Add internal partial Trivial aggregates; no changes to existing game history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f75e841962a7'
down_revision = 'e64f73085196'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('trivial_board_matches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('setup_operation_id', sa.String(36), nullable=False),
        sa.Column('setup_payload', sa.JSON(), nullable=False),
        sa.Column('play_mode', sa.String(16), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('current_turn', sa.Integer(), nullable=False),
        sa.Column('board_version', sa.String(40), nullable=False),
        sa.Column('rules_version', sa.String(40), nullable=False),
        sa.Column('state_schema_version', sa.Integer(), nullable=False),
        sa.Column('board_snapshot', sa.JSON(), nullable=False),
        sa.Column('configuration', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('owner_id', 'setup_operation_id'),
        sa.CheckConstraint("play_mode IN ('LOCAL','ONLINE')"),
        sa.CheckConstraint('version >= 1 AND current_turn >= 1'))
    op.create_index('ix_trivial_board_matches_owner_id', 'trivial_board_matches', ['owner_id'])
    op.create_table('trivial_board_participants',
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('trivial_board_matches.id'), primary_key=True),
        sa.Column('slot', sa.Integer(), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('phase', sa.String(24), nullable=False),
        sa.Column('skip_next_own_turn', sa.Boolean(), nullable=False),
        sa.UniqueConstraint('match_id', 'user_id'),
        sa.CheckConstraint('slot BETWEEN 1 AND 4 AND position BETWEEN 1 AND 140'),
        sa.CheckConstraint("phase IN ('READY','QUESTION_REQUIRED','RULE_PENDING','TURN_ENDED','GOAL_REACHED')"),
        sa.CheckConstraint("NOT skip_next_own_turn OR phase = 'TURN_ENDED'"))
    op.create_index('ix_trivial_board_participants_user_id', 'trivial_board_participants', ['user_id'])
    op.create_table('trivial_board_turns',
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('trivial_board_matches.id'), primary_key=True),
        sa.Column('number', sa.Integer(), primary_key=True),
        sa.Column('participant_slot', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('reason', sa.String(24)),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['match_id', 'participant_slot'], ['trivial_board_participants.match_id', 'trivial_board_participants.slot']),
        sa.CheckConstraint('number >= 1'),
        sa.CheckConstraint("status IN ('OPEN','ENDED','SKIPPED')"))
    op.create_table('trivial_board_operations',
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('trivial_board_matches.id'), primary_key=True),
        sa.Column('operation_id', sa.String(36), primary_key=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('participant_slot', sa.Integer(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['match_id', 'participant_slot'], ['trivial_board_participants.match_id', 'trivial_board_participants.slot']))


def downgrade():
    connection = op.get_bind()
    for name in ('trivial_board_operations', 'trivial_board_turns', 'trivial_board_participants', 'trivial_board_matches'):
        if connection.scalar(sa.text(f'SELECT count(*) FROM {name}')):
            raise RuntimeError('Cannot discard internal Trivial records')
    for name in ('trivial_board_operations', 'trivial_board_turns', 'trivial_board_participants', 'trivial_board_matches'):
        op.drop_table(name)

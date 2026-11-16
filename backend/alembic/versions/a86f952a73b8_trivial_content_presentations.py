"""Private frozen Trivial content and one immutable presentation per arrival."""
from alembic import op
import sqlalchemy as sa

revision='a86f952a73b8'
down_revision='f75e841962a7'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('trivial_board_content_copies',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('match_id',sa.Integer(),sa.ForeignKey('trivial_board_matches.id'),nullable=False),
        sa.Column('question_id',sa.Integer(),sa.ForeignKey('questions.id'),nullable=False),
        sa.Column('bank',sa.String(16),nullable=False),
        sa.Column('difficulty',sa.Integer()),
        sa.Column('snapshot_version',sa.Integer(),nullable=False),
        sa.Column('snapshot',sa.JSON(),nullable=False),
        sa.Column('classification',sa.JSON(),nullable=False),
        sa.Column('binding_snapshot',sa.JSON(),nullable=False),
        sa.Column('copied_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('match_id','bank','question_id'),
        sa.UniqueConstraint('match_id','id'),
        sa.CheckConstraint("bank IN ('LYMPHOCYTE','MACROPHAGE','FLASK','SYRINGE')"),
        sa.CheckConstraint('difficulty IS NULL OR difficulty BETWEEN 1 AND 4'),
        sa.CheckConstraint('snapshot_version = 1'))
    op.create_index('ix_trivial_board_content_copies_match_id','trivial_board_content_copies',['match_id'])
    op.create_table('trivial_board_presentations',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('match_id',sa.Integer(),sa.ForeignKey('trivial_board_matches.id'),nullable=False),
        sa.Column('participant_slot',sa.Integer(),nullable=False),
        sa.Column('turn_number',sa.Integer(),nullable=False),
        sa.Column('cell',sa.Integer(),nullable=False),
        sa.Column('copy_id',sa.Integer(),nullable=False),
        sa.Column('arrival_operation_id',sa.String(36),nullable=False),
        sa.Column('opened_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('deadline_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('match_id','arrival_operation_id'),
        sa.ForeignKeyConstraint(['match_id','copy_id'],['trivial_board_content_copies.match_id','trivial_board_content_copies.id']),
        sa.ForeignKeyConstraint(['match_id','participant_slot'],['trivial_board_participants.match_id','trivial_board_participants.slot']),
        sa.ForeignKeyConstraint(['match_id','turn_number'],['trivial_board_turns.match_id','trivial_board_turns.number']),
        sa.ForeignKeyConstraint(['match_id','arrival_operation_id'],['trivial_board_operations.match_id','trivial_board_operations.operation_id']),
        sa.CheckConstraint('cell BETWEEN 1 AND 140'),
        sa.CheckConstraint('deadline_at > opened_at'))
    op.create_index('ix_trivial_board_presentations_match_id','trivial_board_presentations',['match_id'])
    op.execute("""CREATE FUNCTION trivial_board_private_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Trivial frozen content/presentation is immutable' USING ERRCODE = '23514'; END;
    $$""")
    for table in ('trivial_board_content_copies','trivial_board_presentations'):
        op.execute(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION trivial_board_private_immutable()')


def downgrade():
    connection=op.get_bind()
    for table in ('trivial_board_content_copies','trivial_board_presentations'):
        if connection.scalar(sa.text(f'SELECT count(*) FROM {table}')):
            raise RuntimeError('Cannot discard frozen Trivial content/presentations')
    op.drop_table('trivial_board_presentations')
    op.drop_table('trivial_board_content_copies')
    op.execute('DROP FUNCTION trivial_board_private_immutable()')

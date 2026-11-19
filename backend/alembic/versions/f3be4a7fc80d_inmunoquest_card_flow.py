"""Manual presentations, immutable human verdicts and recoverable deck circulation."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f3be4a7fc80d'
down_revision = 'e2ad396eb7fc'
branch_labels = depends_on = None

PRESENTATION_CHECK = (
    '(presentation_version = 1 AND deadline_at IS NOT NULL AND reader_slot IS NULL '
    'AND request_operation_id IS NULL AND deck_cycle IS NULL) OR '
    '(presentation_version = 2 AND deadline_at IS NULL AND reader_slot IS NOT NULL '
    'AND reader_slot <> participant_slot AND request_operation_id IS NOT NULL AND deck_cycle IS NOT NULL AND deck_cycle >= 1)'
)


def upgrade():
    # No manual presentation was supported by e2. Refuse to invent consumption
    # if a database already contains an unsupported manually inserted one.
    if op.get_bind().scalar(sa.text('SELECT count(*) FROM trivial_board_presentations p '
            'JOIN trivial_board_content_copies c ON c.id=p.copy_id WHERE c.snapshot_version<>1')):
        raise RuntimeError('Cannot infer circulation from unsupported pre-existing presentations')
    op.add_column('trivial_board_presentations', sa.Column('presentation_version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('trivial_board_presentations', sa.Column('reader_slot', sa.Integer()))
    op.add_column('trivial_board_presentations', sa.Column('request_operation_id', sa.String(36)))
    op.add_column('trivial_board_presentations', sa.Column('deck_cycle', sa.Integer()))
    op.alter_column('trivial_board_presentations', 'deadline_at', existing_type=sa.DateTime(timezone=True), nullable=True)
    op.create_unique_constraint('uq_trivial_presentation_match_id', 'trivial_board_presentations', ['match_id', 'id'])
    op.create_unique_constraint('uq_trivial_presentation_request', 'trivial_board_presentations', ['match_id', 'request_operation_id'])
    op.create_foreign_key('fk_trivial_presentation_reader', 'trivial_board_presentations', 'trivial_board_participants',
                          ['match_id', 'reader_slot'], ['match_id', 'slot'])
    op.create_foreign_key('fk_trivial_presentation_request', 'trivial_board_presentations', 'trivial_board_operations',
                          ['match_id', 'request_operation_id'], ['match_id', 'operation_id'])
    op.create_check_constraint('ck_trivial_presentation_version', 'trivial_board_presentations', PRESENTATION_CHECK)
    op.create_table('inmunoquest_deck_states',
        sa.Column('match_id', sa.Integer(), primary_key=True),
        sa.Column('bank', sa.String(16), primary_key=True),
        sa.Column('difficulty', sa.Integer(), primary_key=True),
        sa.Column('circulation_version', sa.String(40), nullable=False),
        sa.Column('cycle', sa.Integer(), nullable=False),
        sa.Column('available_order', sa.JSON(), nullable=False),
        sa.Column('discard_order', sa.JSON(), nullable=False),
        sa.Column('reserved_presentation_id', sa.Integer()),
        sa.ForeignKeyConstraint(['match_id','bank','difficulty'], ['inmunoquest_decks.match_id','inmunoquest_decks.bank','inmunoquest_decks.difficulty']),
        sa.ForeignKeyConstraint(['match_id','reserved_presentation_id'], ['trivial_board_presentations.match_id','trivial_board_presentations.id']),
        sa.UniqueConstraint('match_id','reserved_presentation_id'), sa.CheckConstraint('cycle >= 1'))
    # This is initialization of never-drawn frozen orders, not a catalog reread
    # or a shuffle. Existing copies, orders, engine states and receipts stay intact.
    op.execute("INSERT INTO inmunoquest_deck_states (match_id,bank,difficulty,circulation_version,cycle,available_order,discard_order) "
               "SELECT match_id,bank,difficulty,'inmunoquest-circulation-v1',1,initial_order,'[]'::json FROM inmunoquest_decks")
    op.create_table('inmunoquest_evaluations',
        sa.Column('match_id', sa.Integer(), primary_key=True),
        sa.Column('presentation_id', sa.Integer(), primary_key=True),
        sa.Column('evaluator_slot', sa.Integer(), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('operation_id', sa.String(36), nullable=False),
        sa.Column('correct', sa.Boolean(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['match_id','presentation_id'], ['trivial_board_presentations.match_id','trivial_board_presentations.id']),
        sa.ForeignKeyConstraint(['match_id','evaluator_slot'], ['trivial_board_participants.match_id','trivial_board_participants.slot']),
        sa.ForeignKeyConstraint(['match_id','operation_id'], ['trivial_board_operations.match_id','trivial_board_operations.operation_id']),
        sa.UniqueConstraint('match_id','operation_id'))
    op.execute('CREATE TRIGGER inmunoquest_evaluations_immutable BEFORE UPDATE OR DELETE ON inmunoquest_evaluations '
               'FOR EACH ROW EXECUTE FUNCTION trivial_board_private_immutable()')


def downgrade():
    connection = op.get_bind()
    if (connection.scalar(sa.text('SELECT count(*) FROM inmunoquest_evaluations'))
            or connection.scalar(sa.text('SELECT count(*) FROM trivial_board_presentations WHERE presentation_version<>1'))
            or connection.scalar(sa.text("SELECT count(*) FROM inmunoquest_deck_states s JOIN inmunoquest_decks d "
                "USING(match_id,bank,difficulty) WHERE s.circulation_version<>'inmunoquest-circulation-v1' OR s.cycle<>1 "
                "OR s.reserved_presentation_id IS NOT NULL OR s.discard_order::jsonb<>'[]'::jsonb "
                "OR s.available_order::jsonb<>d.initial_order::jsonb"))):
        raise RuntimeError('Cannot discard InmunoQuest presentations, evaluations or circulation')
    op.drop_table('inmunoquest_evaluations')
    op.drop_table('inmunoquest_deck_states')
    op.drop_constraint('ck_trivial_presentation_version', 'trivial_board_presentations', type_='check')
    op.drop_constraint('fk_trivial_presentation_request', 'trivial_board_presentations', type_='foreignkey')
    op.drop_constraint('fk_trivial_presentation_reader', 'trivial_board_presentations', type_='foreignkey')
    op.drop_constraint('uq_trivial_presentation_request', 'trivial_board_presentations', type_='unique')
    op.drop_constraint('uq_trivial_presentation_match_id', 'trivial_board_presentations', type_='unique')
    op.alter_column('trivial_board_presentations', 'deadline_at', existing_type=sa.DateTime(timezone=True), nullable=False)
    for name in ('deck_cycle','request_operation_id','reader_slot','presentation_version'):
        op.drop_column('trivial_board_presentations', name)

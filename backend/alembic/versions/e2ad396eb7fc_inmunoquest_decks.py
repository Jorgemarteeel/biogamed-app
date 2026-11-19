"""Versioned open copies and immutable automatic initial decks; no card draws."""
from alembic import op
import sqlalchemy as sa

revision = 'e2ad396eb7fc'
down_revision = 'd19c285da6eb'
branch_labels = depends_on = None

COPY_FORMAT_CHECK = (
    "(snapshot_version = 1 AND bank IN ('LYMPHOCYTE','MACROPHAGE','FLASK','SYRINGE')) OR "
    "(snapshot_version = 2 AND bank IN ('LYMPHOCYTE','MACROPHAGE','SPLEEN','FLASK','DNA') "
    "AND difficulty IS NOT NULL AND difficulty BETWEEN 1 AND 4)"
)


def upgrade():
    checks = sa.inspect(op.get_bind()).get_check_constraints('trivial_board_content_copies')
    old = [c for c in checks if 'bank' in c['sqltext'] or 'snapshot_version' in c['sqltext']]
    if len(old) != 2 or any(not c['name'] for c in old):
        raise RuntimeError('Cannot identify historical copy format checks')
    for check in old:
        op.drop_constraint(check['name'], 'trivial_board_content_copies', type_='check')
    op.create_check_constraint('ck_trivial_copy_format_version', 'trivial_board_content_copies', COPY_FORMAT_CHECK)
    op.create_table('inmunoquest_decks',
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('trivial_board_matches.id'), primary_key=True),
        sa.Column('bank', sa.String(16), primary_key=True),
        sa.Column('difficulty', sa.Integer(), primary_key=True),
        sa.Column('shuffle_version', sa.String(40), nullable=False),
        sa.Column('initial_order', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("bank IN ('LYMPHOCYTE','MACROPHAGE','SPLEEN','FLASK','DNA')"),
        sa.CheckConstraint('difficulty BETWEEN 1 AND 4'),
        sa.CheckConstraint('length(shuffle_version) > 0'))
    op.execute('CREATE TRIGGER inmunoquest_decks_immutable BEFORE UPDATE OR DELETE ON inmunoquest_decks '
               'FOR EACH ROW EXECUTE FUNCTION trivial_board_private_immutable()')


def downgrade():
    connection = op.get_bind()
    if (connection.scalar(sa.text('SELECT count(*) FROM inmunoquest_decks'))
            or connection.scalar(sa.text('SELECT count(*) FROM trivial_board_content_copies WHERE snapshot_version <> 1'))
            or connection.scalar(sa.text("SELECT count(*) FROM trivial_board_matches WHERE configuration::jsonb ? 'content_preparation_version'"))):
        raise RuntimeError('Cannot discard prepared InmunoQuest decks')
    op.drop_table('inmunoquest_decks')
    op.drop_constraint('ck_trivial_copy_format_version', 'trivial_board_content_copies', type_='check')
    op.create_check_constraint('trivial_board_content_copies_bank_check', 'trivial_board_content_copies',
                               "bank IN ('LYMPHOCYTE','MACROPHAGE','FLASK','SYRINGE')")
    op.create_check_constraint('trivial_board_content_copies_snapshot_version_check', 'trivial_board_content_copies', 'snapshot_version = 1')

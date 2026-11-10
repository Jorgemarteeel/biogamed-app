"""Minimal trace for administrator role changes."""
from alembic import op
import sqlalchemy as sa
revision='c42d51e63f74'
down_revision='b31c40d52e63'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('user_role_changes',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('actor_id',sa.Uuid(),sa.ForeignKey('users.id'),nullable=False),sa.Column('target_id',sa.Uuid(),sa.ForeignKey('users.id'),nullable=False),sa.Column('previous_role',sa.String(20),nullable=False),sa.Column('new_role',sa.String(20),nullable=False),sa.Column('changed_at',sa.DateTime(timezone=True),nullable=False))

def downgrade():
    raise RuntimeError('Role audit history must be preserved; no automatic downgrade')

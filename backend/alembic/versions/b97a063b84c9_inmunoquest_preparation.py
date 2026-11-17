"""Open question format and immutable preparation configurations. No data conversion."""
from alembic import op
import sqlalchemy as sa
revision="b97a063b84c9"
down_revision="a86f952a73b8"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("questions",sa.Column("reference_answer",sa.Text(),nullable=True))
    op.add_column("questions",sa.Column("bank",sa.String(16),nullable=True))
    op.add_column("questions",sa.Column("note_reference",sa.String(120),nullable=True))
    op.alter_column("questions","topic_id",existing_type=sa.Integer(),nullable=True)
    op.alter_column("questions","correct_answer",existing_type=sa.String(255),nullable=True)
    op.create_check_constraint("ck_question_open_format","questions","(question_type = 'INMUNOQUEST' AND topic_id IS NULL AND reference_answer IS NOT NULL AND length(trim(reference_answer)) > 0 AND bank IS NOT NULL AND bank IN ('LYMPHOCYTE','MACROPHAGE','SPLEEN','FLASK','DNA') AND difficulty IS NOT NULL AND difficulty BETWEEN 1 AND 4 AND (options IS NULL OR options::jsonb = 'null'::jsonb) AND correct_option_index IS NULL AND exact_word IS NULL AND letter IS NULL) OR (question_type <> 'INMUNOQUEST' AND topic_id IS NOT NULL AND correct_answer IS NOT NULL AND reference_answer IS NULL AND bank IS NULL AND note_reference IS NULL)")
    op.create_table("inmunoquest_configurations",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("name",sa.String(255),nullable=False),sa.Column("version",sa.Integer(),nullable=False),sa.Column("subject_id",sa.Integer(),sa.ForeignKey("subjects.id"),nullable=True),sa.Column("definition",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("name","version"))

def downgrade():
    bind=op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM questions WHERE question_type='INMUNOQUEST'")) or bind.scalar(sa.text("SELECT count(*) FROM inmunoquest_configurations")):
        raise RuntimeError("Downgrade blocked: preserve open questions and configurations")
    op.drop_table("inmunoquest_configurations")
    op.drop_constraint("ck_question_open_format","questions",type_="check")
    op.alter_column("questions","topic_id",existing_type=sa.Integer(),nullable=False)
    op.alter_column("questions","correct_answer",existing_type=sa.String(255),nullable=False)
    for name in ["reference_answer","bank","note_reference"]:op.drop_column("questions",name)

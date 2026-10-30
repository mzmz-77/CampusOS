"""Add source registry and immutable audit records; preserve phase-one messages."""
from alembic import op
import sqlalchemy as sa

revision = '0002_sources'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('sources',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('public_website', sa.Boolean, nullable=False),
        sa.Column('access_method', sa.String(30), nullable=False),
        sa.Column('authorization_status', sa.String(30), nullable=False),
        sa.Column('authorization_scope', sa.Text, nullable=False),
        sa.Column('authorization_reference', sa.Text, nullable=False),
        sa.Column('authorization_expires_at', sa.DateTime(timezone=True)),
        sa.Column('enabled', sa.Boolean, nullable=False),
        sa.Column('revision', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("access_method IN ('unconfigured','manual_import','public_web')", name='ck_source_method'),
        sa.CheckConstraint("authorization_status IN ('not_requested','pending','granted','revoked')", name='ck_source_auth'))
    op.create_table('source_events',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('source_id', sa.Integer, sa.ForeignKey('sources.id'), nullable=False),
        sa.Column('action', sa.String(40), nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('before_json', sa.Text),
        sa.Column('after_json', sa.Text, nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_source_events_source_id', 'source_events', ['source_id'])
    if op.get_bind().dialect.name == 'sqlite':
        # SQLite supports a nullable inline reference without rebuilding messages.
        # Rebuilding would risk the existing origins -> messages foreign key.
        op.execute('ALTER TABLE messages ADD COLUMN source_id INTEGER REFERENCES sources(id)')
    else:
        op.add_column('messages', sa.Column('source_id', sa.Integer,
            sa.ForeignKey('sources.id', name='fk_messages_source_id')))
    op.add_column('messages', sa.Column('authorization_snapshot', sa.Text))


def downgrade():
    raise RuntimeError('Destructive downgrade is disabled; restore a verified backup instead.')

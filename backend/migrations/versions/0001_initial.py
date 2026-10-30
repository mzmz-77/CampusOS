"""Frozen phase-one schema. Existing matching databases may be stamped here."""
import sqlalchemy as sa
from alembic import op

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def metadata():
    m = sa.MetaData()
    sa.Table('messages', m,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('external_id', sa.String(200)),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('source_url', sa.Text),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('source', 'external_id'))
    sa.Table('notifications', m,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('summary', sa.Text, nullable=False),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('deadline', sa.DateTime(timezone=True)),
        sa.Column('warnings', sa.Text, nullable=False),
        sa.Column('parser_version', sa.String(30), nullable=False),
        sa.Column('fingerprint', sa.String(64), unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    sa.Table('origins', m,
        sa.Column('message_id', sa.Integer, sa.ForeignKey('messages.id'), primary_key=True),
        sa.Column('notification_id', sa.Integer, sa.ForeignKey('notifications.id'), nullable=False, index=True))
    sa.Table('tasks', m,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('notes', sa.Text, nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('deadline', sa.DateTime(timezone=True)),
        sa.Column('notification_id', sa.Integer, sa.ForeignKey('notifications.id'), unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False))
    return m


def upgrade():
    metadata().create_all(op.get_bind(), checkfirst=False)


def downgrade():
    raise RuntimeError('Destructive downgrade is disabled; restore a verified backup instead.')

from datetime import datetime, timezone
from sqlalchemy import create_engine, event, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator

class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True
    def process_bind_param(self, value, dialect):
        if value is None: return None
        if value.tzinfo is None: raise ValueError("Timezone is required")
        return value.astimezone(timezone.utc)
    def process_result_value(self, value, dialect):
        if value is None: return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)



def now(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass

class Message(Base):
    __tablename__ = 'messages'
    __table_args__ = (UniqueConstraint('source', 'external_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(100))
    external_id: Mapped[str | None] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    received_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)


def make_engine(url):
    kwargs = {}
    if url.startswith('sqlite'):
        kwargs['connect_args'] = {'check_same_thread': False}
        if url in ('sqlite://', 'sqlite:///:memory:'): kwargs['poolclass'] = StaticPool
    engine = create_engine(url, **kwargs)
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def enable_fk(connection, _): connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    return engine

class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30))
    priority: Mapped[str] = mapped_column(String(20))
    deadline: Mapped[datetime | None] = mapped_column(UTCDateTime())
    warnings: Mapped[str] = mapped_column(Text)
    parser_version: Mapped[str] = mapped_column(String(30), default='rules-v1')
    fingerprint: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)

class Origin(Base):
    __tablename__ = 'origins'
    message_id: Mapped[int] = mapped_column(ForeignKey('messages.id'), primary_key=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey('notifications.id'), index=True)

class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(20), default='todo')
    priority: Mapped[str] = mapped_column(String(20), default='normal')
    deadline: Mapped[datetime | None] = mapped_column(UTCDateTime())
    notification_id: Mapped[int | None] = mapped_column(ForeignKey('notifications.id'), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)

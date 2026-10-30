import os
import json
from contextlib import asynccontextmanager
import secrets
from datetime import timezone
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from .database import make_engine, Message, Notification, Origin, Task, Source, SourceEvent, now
from .schemas import MessageIn, TaskIn, TaskPatch, SourcePatch
from .parser import parse
from .dedup import fingerprint
from .migrate import database_url as configured_database_url, ensure_database
from .sources import seed_catalog, source_view, source_state, encoded, apply_source_patch, registered_message_source


def record(obj):
    result = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    if isinstance(obj, Message) and obj.authorization_snapshot:
        result['authorization_snapshot'] = json.loads(obj.authorization_snapshot)
    return result


def create_app(database_url: str | None = None):
    engine = make_engine(database_url or configured_database_url())

    @asynccontextmanager
    async def lifespan(app):
        ensure_database(engine)
        seed_catalog(engine)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title='CampusOS-XDU', version='0.2.0', lifespan=lifespan)
    app.state.engine = engine
    bearer = HTTPBearer(auto_error=False)
    token = os.getenv('CAMPUSOS_API_TOKEN')
    def authorize(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if token and (not credentials or not secrets.compare_digest(credentials.credentials, token)):
            raise HTTPException(401, '访问令牌无效')
    def db():
        with Session(engine) as session: yield session

    @app.get('/api/health')
    def health(): return {'status': 'ok'}

    @app.post('/api/messages', status_code=201, dependencies=[Depends(authorize)])
    def ingest(payload: MessageIn, session: Session = Depends(db)):
        values = payload.model_dump(mode='json')
        values['published_at'] = payload.published_at.astimezone(timezone.utc) if payload.published_at else None
        if payload.source_id is not None:
            _, values['authorization_snapshot'] = registered_message_source(session, payload.source_id)
        message = Message(**values)
        session.add(message)
        try: session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.scalar(select(Message).where(Message.source == payload.source, Message.external_id == payload.external_id))
            if existing is None: raise HTTPException(409, '消息保存冲突，请重试')
            old_time = existing.published_at
            if old_time is not None and old_time.tzinfo is None: old_time = old_time.replace(tzinfo=timezone.utc)
            if any(getattr(existing,k) != values[k] for k in ('source','external_id','content','source_url','source_id')) or old_time != payload.published_at:
                raise HTTPException(409, '相同来源编号的原文或元数据冲突')
            return record(existing)
        session.refresh(message)
        return record(message)

    @app.get('/api/messages', dependencies=[Depends(authorize)])
    def messages(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), session: Session = Depends(db)):
        return [record(m) for m in session.scalars(select(Message).order_by(Message.id.desc()).offset(offset).limit(limit))]

    @app.get('/api/messages/{message_id}', dependencies=[Depends(authorize)])
    def message(message_id: int, session: Session = Depends(db)):
        row = session.get(Message, message_id)
        if row is None: raise HTTPException(404, '消息不存在')
        return record(row)

    @app.post('/api/messages/{message_id}/parse', dependencies=[Depends(authorize)])
    def parse_message(message_id: int, session: Session = Depends(db)):
        raw = session.get(Message, message_id)
        if raw is None: raise HTTPException(404, '消息不存在')
        origin = session.get(Origin, message_id)
        if origin: return record(session.get(Notification, origin.notification_id))
        digest = fingerprint(raw.content)
        notification = session.scalar(select(Notification).where(Notification.fingerprint == digest))
        if notification is None:
            notification = Notification(**parse(raw.content), fingerprint=digest)
            session.add(notification)
            try: session.flush()
            except IntegrityError:
                session.rollback()
                notification = session.scalar(select(Notification).where(Notification.fingerprint == digest))
                if notification is None: raise HTTPException(409, '解析冲突，请重试')
        session.add(Origin(message_id=message_id, notification_id=notification.id))
        try: session.commit()
        except IntegrityError:
            session.rollback()
            origin = session.get(Origin, message_id)
            if origin is None: raise HTTPException(409, '来源关联冲突，请重试')
            notification = session.get(Notification, origin.notification_id)
        session.refresh(notification)
        return record(notification)

    @app.get('/api/notifications', dependencies=[Depends(authorize)])
    def notifications(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), session: Session = Depends(db)):
        return [record(n) for n in session.scalars(select(Notification).order_by(Notification.id.desc()).offset(offset).limit(limit))]

    @app.get('/api/tasks', dependencies=[Depends(authorize)])
    def tasks(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), session: Session = Depends(db)):
        return [record(t) for t in session.scalars(select(Task).order_by(Task.id.desc()).offset(offset).limit(limit))]

    @app.post('/api/tasks', status_code=201, dependencies=[Depends(authorize)])
    def create_task(payload: TaskIn, session: Session = Depends(db)):
        if payload.notification_id and session.get(Notification, payload.notification_id) is None:
            raise HTTPException(404, '通知不存在')
        task = Task(**payload.model_dump())
        session.add(task)
        try: session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, '该通知已有任务')
        session.refresh(task)
        return record(task)

    @app.patch('/api/tasks/{task_id}', dependencies=[Depends(authorize)])
    def edit_task(task_id: int, payload: TaskPatch, session: Session = Depends(db)):
        task = session.get(Task, task_id)
        if task is None: raise HTTPException(404, '任务不存在')
        values = payload.model_dump(exclude_unset=True)
        if any(v is None and k != 'deadline' for k,v in values.items()): raise HTTPException(422, '仅截止时间允许清空')
        for key,value in values.items(): setattr(task,key,value)
        task.updated_at = now()
        session.commit()
        session.refresh(task)
        return record(task)

    @app.get('/api/notifications/{notification_id}', dependencies=[Depends(authorize)])
    def notification_detail(notification_id: int, session: Session = Depends(db)):
        notification = session.get(Notification, notification_id)
        if notification is None: raise HTTPException(404, '通知不存在')
        sources = session.scalars(select(Message).join(Origin, Origin.message_id == Message.id).where(Origin.notification_id == notification_id).order_by(Message.id))
        task = session.scalar(select(Task).where(Task.notification_id == notification_id))
        return {**record(notification), 'sources':[record(m) for m in sources], 'task':record(task) if task else None}

    @app.get('/api/tasks/{task_id}/trace', dependencies=[Depends(authorize)])
    def task_trace(task_id: int, session: Session = Depends(db)):
        task = session.get(Task, task_id)
        if task is None: raise HTTPException(404, '任务不存在')
        return {'task':record(task), 'notification':notification_detail(task.notification_id, session) if task.notification_id else None}

    @app.get('/api/sources', dependencies=[Depends(authorize)])
    def sources(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), session: Session = Depends(db)):
        return [source_view(source) for source in session.scalars(select(Source).order_by(Source.id).offset(offset).limit(limit))]

    @app.get('/api/sources/{source_id}', dependencies=[Depends(authorize)])
    def source_detail(source_id: int, session: Session = Depends(db)):
        source = session.get(Source, source_id)
        if source is None: raise HTTPException(404, '登记来源不存在。')
        return source_view(source)

    @app.get('/api/sources/{source_id}/events', dependencies=[Depends(authorize)])
    def source_events(source_id: int, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), session: Session = Depends(db)):
        if session.get(Source, source_id) is None: raise HTTPException(404, '登记来源不存在。')
        events = session.scalars(select(SourceEvent).where(SourceEvent.source_id == source_id).order_by(SourceEvent.id.desc()).offset(offset).limit(limit))
        return [{'id': e.id, 'source_id': e.source_id, 'action': e.action, 'reason': e.reason,
                 'before': json.loads(e.before_json) if e.before_json else None,
                 'after': json.loads(e.after_json), 'occurred_at': e.occurred_at} for e in events]

    @app.patch('/api/sources/{source_id}', dependencies=[Depends(authorize)])
    def edit_source(source_id: int, payload: SourcePatch, session: Session = Depends(db)):
        source = session.scalar(select(Source).where(Source.id == source_id).with_for_update())
        if source is None: raise HTTPException(404, '登记来源不存在。')
        before = apply_source_patch(source, payload)
        try:
            session.flush()
            action = 'authorization_granted' if payload.authorization_status == 'granted' else 'updated'
            session.add(SourceEvent(source_id=source.id, action=action, reason=payload.reason,
                                    before_json=encoded(before), after_json=encoded(source_state(source))))
            session.commit()
        except StaleDataError:
            session.rollback()
            raise HTTPException(409, '来源已被更新，请刷新后重试。')
        session.refresh(source)
        return source_view(source)

    return app

app = create_app()

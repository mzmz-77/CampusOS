import os
import secrets
from pathlib import Path
from datetime import timezone
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .database import make_engine, Message, Notification, Origin, Task, now
from .schemas import MessageIn, TaskIn, TaskPatch
from .parser import parse
from .dedup import fingerprint


def record(obj): return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def create_app(database_url: str | None = None):
    default_db = Path(__file__).resolve().parents[1] / 'campusos.db'
    engine = make_engine(database_url or os.getenv('DATABASE_URL', f'sqlite:///{default_db}'))
    app = FastAPI(title='CampusOS-XDU', version='0.1.0')
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
        message = Message(**values)
        session.add(message)
        try: session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.scalar(select(Message).where(Message.source == payload.source, Message.external_id == payload.external_id))
            if existing is None: raise HTTPException(409, '消息保存冲突，请重试')
            old_time = existing.published_at
            if old_time is not None and old_time.tzinfo is None: old_time = old_time.replace(tzinfo=timezone.utc)
            if any(getattr(existing,k) != values[k] for k in ('source','external_id','content','source_url')) or old_time != payload.published_at:
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

    return app

app = create_app()

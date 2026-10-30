"""Registry and authorization bookkeeping only: no external network access."""
import json
from datetime import timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Source, SourceEvent, now

CATALOG = (
    ('xdu_website', '西电学校官网', True),
    ('cs_website', '西电计算机科学与技术学院官网', True),
    ('wechat_official', '学校微信公众号', False),
    ('wechat_enterprise', '学校微信企业号', False),
    ('qq_group', 'QQ 群', False),
    ('wechat_group', '微信群', False),
    ('learning_xdu', '学在西电', False),
    ('xdyou', 'XDYou', False),
)


def source_state(source):
    return {column.name: getattr(source, column.name) for column in source.__table__.columns}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, default=lambda date: date.isoformat())


def seed_catalog(engine):
    with Session(engine) as session:
        existing = set(session.scalars(select(Source.code)))
        for code, name, public in CATALOG:
            if code in existing:
                continue
            source = Source(code=code, name=name, public_website=public,
                            access_method='public_web' if public else 'unconfigured')
            session.add(source)
            session.flush()
            session.add(SourceEvent(source_id=source.id, action='registered', reason='登记目标来源；尚未取得接入授权。',
                                    before_json=None, after_json=encoded(source_state(source))))
        session.commit()


def authorization_valid(source):
    return (source.authorization_status == 'granted'
            and bool(source.authorization_scope.strip())
            and bool(source.authorization_reference.strip())
            and (source.authorization_expires_at is None or source.authorization_expires_at > now()))


def source_view(source):
    if source.authorization_status == 'granted' and source.authorization_expires_at and source.authorization_expires_at <= now():
        status = 'authorization_expired'
    elif not authorization_valid(source):
        status = 'authorization_required'
    elif source.access_method == 'unconfigured':
        status = 'unconfigured'
    elif source.access_method == 'public_web':
        status = 'not_implemented'
    elif not source.enabled:
        status = 'disabled'
    else:
        status = 'ready_for_manual_import'
    return {**source_state(source), 'integration_status': status,
            'effective_enabled': status == 'ready_for_manual_import',
            'capabilities': {'manual_import': True, 'public_web': False}}


def apply_source_patch(source, payload):
    if source.revision != payload.expected_revision:
        raise HTTPException(409, '来源已被更新，请刷新后重试。')
    before = source_state(source)
    values = payload.model_dump(exclude_unset=True, exclude={'reason', 'expected_revision', 'authorization_confirmed'})
    if any(value is None and key != 'authorization_expires_at' for key, value in values.items()):
        raise HTTPException(422, '仅授权有效期允许清空。')
    method = values.get('access_method', source.access_method)
    status = values.get('authorization_status', source.authorization_status)
    if method == 'public_web' and not source.public_website:
        raise HTTPException(422, '该来源未被登记为公开网站，不能选择公开网页方式。')
    grant_fields = {'authorization_status', 'authorization_scope', 'authorization_reference', 'authorization_expires_at', 'access_method'}
    if status == 'granted' and grant_fields.intersection(values):
        scope = values.get('authorization_scope', source.authorization_scope)
        reference = values.get('authorization_reference', source.authorization_reference)
        expires = values.get('authorization_expires_at', source.authorization_expires_at)
        if not payload.authorization_confirmed or not scope.strip() or not reference.strip():
            raise HTTPException(422, '登记已授权状态必须确认真实授权，并填写授权范围与依据。')
        if expires and expires <= now():
            raise HTTPException(422, '授权有效期必须晚于当前时间。')
    for key, value in values.items():
        if key == 'authorization_expires_at' and value:
            value = value.astimezone(timezone.utc)
        setattr(source, key, value)
    can_enable = authorization_valid(source) and source.access_method == 'manual_import'
    if values.get('enabled') is True and not can_enable:
        raise HTTPException(409, '仅真实授权有效且选择手工录入的来源可启用；自动采集尚未实现。')
    if not can_enable:
        source.enabled = False
    source.updated_at = now()
    return before


def registered_message_source(session, source_id):
    source = session.scalar(select(Source).where(Source.id == source_id).with_for_update())
    if source is None:
        raise HTTPException(404, '登记来源不存在。')
    if not source_view(source)['effective_enabled']:
        raise HTTPException(409, '该来源尚未启用、授权无效或接入方式未实现，请先检查来源设置。')
    event = session.scalar(select(SourceEvent).where(SourceEvent.source_id == source_id,
        SourceEvent.action == 'authorization_granted').order_by(SourceEvent.id.desc()))
    return source, encoded({
        'source_id': source.id, 'source_name': source.name, 'access_method': source.access_method,
        'authorization_status': source.authorization_status, 'scope': source.authorization_scope,
        'reference': source.authorization_reference, 'expires_at': source.authorization_expires_at,
        'authorization_event_id': event.id if event else None, 'captured_at': now(),
    })

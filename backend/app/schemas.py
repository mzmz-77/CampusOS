from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator

class MessageIn(BaseModel):
    source_id: int | None = Field(default=None, gt=0)
    source: str = Field(min_length=1, max_length=100)
    external_id: str | None = Field(default=None, min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=50000)
    source_url: HttpUrl | None = None
    published_at: datetime | None = None

    @field_validator('source', 'content', 'external_id')
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip(): raise ValueError('不得为空白')
        return value

    @field_validator('published_at')
    @classmethod
    def aware(cls, value):
        if value is not None and value.tzinfo is None: raise ValueError('时间必须包含时区')
        return value

from typing import Literal

class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    notes: str = Field(default='', max_length=10000)
    priority: Literal['normal','high'] = 'normal'
    deadline: datetime | None = None
    notification_id: int | None = Field(default=None, gt=0)
    _nonblank = field_validator('title')(MessageIn.nonblank.__func__)
    _aware = field_validator('deadline')(MessageIn.aware.__func__)

class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=10000)
    status: Literal['todo','doing','done'] | None = None
    priority: Literal['normal','high'] | None = None
    deadline: datetime | None = None
    _nonblank = field_validator('title')(MessageIn.nonblank.__func__)
    _aware = field_validator('deadline')(MessageIn.aware.__func__)


class SourcePatch(BaseModel):
    model_config = {'extra': 'forbid'}
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=1000)
    access_method: Literal['unconfigured', 'manual_import', 'public_web'] | None = None
    authorization_status: Literal['not_requested', 'pending', 'granted', 'revoked'] | None = None
    authorization_scope: str | None = Field(default=None, max_length=2000)
    authorization_reference: str | None = Field(default=None, max_length=1000)
    authorization_expires_at: datetime | None = None
    authorization_confirmed: bool = False
    enabled: bool | None = None
    _reason_nonblank = field_validator('reason')(MessageIn.nonblank.__func__)
    _aware = field_validator('authorization_expires_at')(MessageIn.aware.__func__)

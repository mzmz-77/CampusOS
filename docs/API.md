# API 说明

完整请求模型、字段限制和返回结构见运行中的 `/docs` 或 `/openapi.json`。

设置 `CAMPUSOS_API_TOKEN` 后，除健康检查外的业务 API 均需要 `Authorization: Bearer <token>`。

| 方法 | 路径 | 行为 |
|---|---|---|
| GET | /api/health | 健康检查 |
| POST | /api/messages | 保存原文，201；来源编号冲突 409 |
| GET | /api/messages | 分页列出原文，最新在前 |
| GET | /api/messages/{id} | 原文及来源元数据 |
| POST | /api/messages/{id}/parse | 幂等解析并归并重复正文 |
| GET | /api/notifications | 分页列出通知 |
| GET | /api/notifications/{id} | 解析结果、所有原始来源、关联任务 |
| POST | /api/tasks | 创建任务；同一通知重复建任务返回 409 |
| GET | /api/tasks | 分页列出任务 |
| PATCH | /api/tasks/{id} | 修改标题、备注、状态、优先级、截止时间 |
| GET | /api/tasks/{id}/trace | 任务 → 通知 → 所有原始消息 |

所有列表接受 `limit=100&offset=0`，最大 limit 为 500。对象不存在返回 404，输入验证失败返回 422。

消息示例（仅提交到本项目 API，不访问任何平台）：

```json
{
  "source": "手工录入",
  "external_id": "optional-local-id",
  "content": "粘贴已获授权的完整原文",
  "source_url": null,
  "published_at": "2026-10-30T20:00:00+08:00"
}
```

创建任务必填 `title`；可选 `notes`、`priority`（normal/high）、`deadline`（带时区或 null）、`notification_id`。新任务状态为 todo。

任务状态为 `todo`、`doing`、`done`；PATCH 只修改请求中提供的字段，`deadline: null` 可清空截止时间，其他字段不接受显式 null。通知中的解析结果保留不变，人工修正体现在任务上，便于对照原始依据。

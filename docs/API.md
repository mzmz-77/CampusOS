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


## 来源注册与授权（v0.2）

新增接口与其他业务 API 使用相同的可选 Bearer 令牌保护：

| 方法 | 路径 | 行为 |
|---|---|---|
| GET | /api/sources | 按登记顺序分页列出八类目标来源 |
| GET | /api/sources/{id} | 来源设置、有效授权与接入状态 |
| PATCH | /api/sources/{id} | 乐观版本校验后修改授权或启用设置 |
| GET | /api/sources/{id}/events | 分页读取不可改写的变更记录，最新在前 |

来源名称、代码和公开网站类别由系统固定，不能通过 PATCH 改成其他平台。没有删除来源或修改历史事件的接口。所有更新需要 `expected_revision`（上次 GET 的 revision）与非空 `reason`；版本过期返回 409，不自动覆盖。

`access_method` 支持 `unconfigured`、`manual_import` 和仅公开网站可选的 `public_web`。`authorization_status` 支持 `not_requested`、`pending`、`granted`、`revoked`。登记 / 修改已授权信息需要 `authorization_confirmed: true`、非空 `authorization_scope` / `authorization_reference`，可提供带时区的 `authorization_expires_at`。依据应为可核验的授权说明或文档编号，不提交密码或访问令牌。

授权记录只表示操作者已登记相应依据，不表示系统已向学校或平台核验。API 不获取或验证私人校园账号，也不发起任何平台连接。

`enabled` 是操作者设置；`effective_enabled` 是每次读取 / 接入时计算的有效状态，授权过期时即使之前 enabled 为 true 也不会允许消息。当前只有有效授权下的 `manual_import` 可以启用。公开网页采集未实现，显式请求启用时返回 409；撤销授权会自动禁用。

消息输入新增可选 `source_id`。提供时，后端在保存前检查登记来源是否有效启用，并保存不可改写的 `authorization_snapshot`，包含来源、授权范围、依据、有效期及授权事件编号。未提供时保留普通手工录入兼容性，快照为空，不声称该标签已获得平台认证。

授权失效不删除历史原文、任务、来源关系或快照。重复来源编号冲突检查也会比较 `source_id`，不会将原文重新归属到其他登记来源。

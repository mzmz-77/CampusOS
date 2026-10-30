# CampusOS-XDU

校园事务工作台。将获授权的原始消息保存为不可改写的记录，通过本地规则提取通知，再转为可管理、可追溯的任务。

第一阶段已实现：前后端项目结构、消息接入 API、原文持久化、通知解析、任务管理、来源追溯、重复通知合并、可视化管理界面和 PWA 应用壳。

初始化验收后已加入八类来源注册、授权状态、手工接入开关、授权变更记录及录入时授权快照。所有目标来源初始均未授权、禁用，自动采集尚未实现。

## 环境与启动

需要 Python 3.12+、Node.js 22.12+ / 24+、npm。所有依赖安装在本项目内，不需要全局依赖。

```bash
cd /workspace/CampusOS
make setup
make dev
```

首次使用空数据库时会在启动时执行初始化迁移。更新已有项目后，先运行 `make setup` 更新项目内依赖，再运行 `make migrate` 升级数据库，最后 `make dev`。

- 工作台：http://127.0.0.1:5173
- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health
- 使用 Ctrl+C 停止两个服务。

不使用 Make 时，分别启动：

```bash
# 终端一，从项目根目录执行
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
# 终端二，从项目根目录执行
cd frontend
npm run dev -- --port 5173 --strictPort
```

## 检查

```bash
make test
make build
```

后端测试使用临时 SQLite 文件或内存数据库；前端交互测试仅模拟本项目自己的 API 响应。测试夹具没有读取或冒充任何第三方平台。

生产构建位于 `frontend/dist`。本地检查 PWA 时，保持后端运行，再执行：

```bash
cd frontend
npm exec vite preview -- --host 127.0.0.1 --port 4173
```

访问 http://127.0.0.1:4173 。开发模式不注册 Service Worker；生产构建在 localhost 或 HTTPS 下注册。首次在线加载后，应用壳可离线打开，业务数据依然需要后端连接。API、令牌、原文及任务响应不进入 Service Worker 缓存。浏览器支持安装时会出现安装按钮。

## 使用流程

1. 点击“录入消息”，填写来源名称和原文，可补充原文链接、来源编号、发布时间。
2. 选择保存后解析，或从“原始消息”中手动解析。
3. 在通知详情核对标题、类别、优先级、截止时间和完整原文。
4. 点击“转为任务”，之后可以编辑、标记进行中或已完成。
5. 在任务编辑框点击“追溯通知和原始来源”查看依据。

无预置业务数据。来源名称是提交者提供的标签，不代表系统验证了来源真实性。原文链接只由用户手动打开，服务端不会抓取链接。

## 数据与规则

- 默认数据库：`backend/campusos.db`。所有时间按 UTC 存储，界面以北京时间显示；API 输入时间必须包含时区。
- 原始消息不提供编辑或删除接口，原文、来源标识、URL、发布时间和接收时间一并保存。
- `(source, external_id)` 有值时唯一；重复相同输入返回原记录，内容或元数据冲突返回 409。无来源编号的每次提交保留为独立原文。
- 解析为本地 `rules-v1`，不使用 DeepSeek 或任何外部模型。标题取首行首句；类别和紧急度按关键词提取。
- 仅识别含“截止 / 截至 / 最晚”的同一行中唯一、带年份和时分的日期，如 `截止 2026年11月2日 18:00`。不推测“明天”“周五”或缺失年份；无效 / 多个候选时间保留为空并提示核对。规则结果需人工核对，任务可编辑。
- 去重：正文 NFC 规范化、连续空白合并后计算 SHA-256。完全相同的正文关联同一通知；每条原文和来源均保留。日期、文字和标点不同不自动模糊合并。重复解析同一消息不会重复创建来源。
- 每条通知最多关联一个任务；手工任务允许没有来源。
- 列表 API 使用 `limit`（1–500）和 `offset`。界面逐页加载全部记录用于搜索和统计；大规模数据的服务端搜索为后续工作。

## PostgreSQL

使用 SQLAlchemy，已包含 psycopg 驱动。可在已准备好的空 PostgreSQL 数据库上，用单条命令的局部变量启动：

```bash
cd backend
DATABASE_URL='postgresql+psycopg://user:password@localhost/campusos' ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

该设置只作用于这条命令，不写全局变量。空数据库启动时通过 Alembic 初始化，已有数据库必须先执行迁移，**不会复制 SQLite 数据**：

```bash
cd backend
DATABASE_URL='postgresql+psycopg://user:password@localhost/campusos' ../.venv/bin/python -m app.migrate
```

本地回归使用 SQLite。CI 工作流提供独立 PostgreSQL 16 测试服务，配置 `CAMPUSOS_TEST_POSTGRES_URL` 后才运行实库测试；测试在专用 `*_test` 数据库中创建临时 schema 并清理，不能配置业务数据库。

## 访问范围

默认仅绑定 `127.0.0.1`，作为单用户本地工作台。未实现多用户身份隔离，不应直接作为公网服务使用。如果需要本地令牌保护，用命令局部变量设置 `CAMPUSOS_API_TOKEN`；在界面“消息接入”中填入相同令牌。令牌仅在当前浏览器标签会话中保存。健康检查公开，其余业务接口统一校验配置的令牌。

没有任何第三方平台连接器、私人账号读取、自动登录、爬虫或平台接口模拟。后续平台接入必须先取得真实授权。

## 目录

```text
backend/app/          FastAPI、SQLAlchemy 模型、解析与去重
backend/tests/        API、持久化、任务、追溯、去重测试
frontend/src/         React + TypeScript 界面与交互测试
frontend/public/      PWA manifest、图标、Service Worker
scripts/dev.py        项目内一键启动
docs/                API 说明、测试与实施记录
```

详见 `docs/API.md`、`docs/PROGRESS.md`、`docs/TEST_REPORT.md`、`docs/INITIALIZATION_ACCEPTANCE.md` 和 `docs/PHASE3_SOURCES.md`。

## 托管交互体验

体验地址：https://campusos-xdu-experience.mightytiger3.chatgpt.site （私有站点，可能需要登录 ChatGPT）。

为远程环境缺少端口转发的情况提供独立的浏览器体验入口，使用同一 React 界面。

```bash
cd frontend
npm run build:experience
```

此构建启用 `src/preview.ts` 的浏览器本地体验数据层，使用 IndexedDB 保存用户主动录入的消息、解析结果、来源关系和任务。刷新或重新打开同一浏览器时数据保留；清除本站数据会删除体验记录，不在设备间同步。体验版不调用远程 FastAPI，也不把消息发送给第三方平台，页面顶部明确标注。

普通 `npm run build`、`npm run dev` 仍访问真实 FastAPI；体验数据层仅在 `hosted-preview` 构建模式启用。服务端 API 不由托管体验版提供。

`.openai/hosting.json` 记录该体验站点的身份及静态构建目录。发布源码在独立的 Sites Git 仓库中同步，不修改原项目 Git 远端配置。


## 来源与授权管理

在“消息接入 → 目标来源与授权”管理学校官网、计算机科学与技术学院官网、学校公众号、学校企业号、QQ 群、微信群、学在西电、XDYou 八类来源。

1. 初始均为“未申请”且禁用，不登记校园账号或猜测 API。
2. 取得真实授权后，填写授权范围、依据、有效期及变更原因，并主动确认后登记授权。程序只记录操作者声明，不代替平台核验。
3. 选择“手工录入”，再单独启用。当前公开网页采集尚未实现，不能启用自动采集。
4. 在录入框关联已启用来源，后端再次检查授权状态、有效期和接入方式；授权撤销 / 到期后拒绝该来源的新消息。
5. 原始消息保存录入时授权快照，通知详情可查看；变更记录只增不改。没有关联来源的旧消息保持原样，普通手工标签不代表来源已验证。

## 数据库迁移

```bash
make migrate        # SQLite 文件升级前自动备份并校验备份
make migrate-check  # 检查是否达到当前迁移版本
```

当前版本为 `0002_sources`，迁移脚本位于 `backend/migrations/versions/`。升级初期未版本化数据库前，会校验原四张表的列、类型、主键、唯一约束及外键；不匹配就停止。SQLite 备份保存在被 Git 忽略的 `work/backups/`。PostgreSQL 变更前由部署者准备数据库备份；本命令不代做 PostgreSQL 备份。

已有数据库不会在 Web 请求或应用启动时自动升级。降级删除数据的操作已禁用；如需回退，停止服务后使用经过验证的数据库备份及匹配的代码版本。

## 持续集成

`.github/workflows/checks.yml` 在 push / pull request 时安装项目内依赖、执行 SQLite 与独立 PostgreSQL 回归、前端测试及两种构建。CI 中的数据库凭据仅用于一次性测试服务，与学校账号无关。本地没有设置 `CAMPUSOS_TEST_POSTGRES_URL` 时，实库测试明确跳过。

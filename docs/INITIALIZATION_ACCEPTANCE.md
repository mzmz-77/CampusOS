# CampusOS-XDU 第二阶段：项目初始化验收

验收日期：2026-10-30（北京时间）  
项目目录：`/workspace/CampusOS`  
受检提交：`f5820007e71788a78229c4a4391ecd4200fcdc96`

结论：**本地单用户、SQLite 范围的项目初始化验收通过。** 此结论不代表校园数据源接入、PostgreSQL 实库验证、多用户生产服务或远程 FastAPI 部署已完成。

本轮仅检查已有项目、执行已有测试和构建、验证进程启动并记录本文档，没有修改业务代码或安装依赖。没有进行校园账号登录、第三方平台接口探测、系统全局配置修改或其他项目修改。下一阶段开发等待用户确认。

## A. 当前项目结构

```text
CampusOS/
├── README.md
├── Makefile                       # setup / dev / test / build
├── package.json                   # 根目录 build 为托管体验版构建入口
├── .gitignore
├── .openai/hosting.json            # Sites 体验站点身份及静态 dist 目录
├── backend/
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── campusos.db                 # 本地 SQLite，已被 Git 忽略
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 应用与 API
│   │   ├── database.py             # SQLAlchemy 模型、连接及 UTC 类型
│   │   ├── schemas.py              # Pydantic 请求校验
│   │   ├── parser.py               # 本地规则解析
│   │   └── dedup.py                # 正文规范化与 SHA-256 去重
│   └── tests/                     # conftest + 8 个测试模块
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── src/                       # React 界面、API 客户端、体验数据层及测试
│   ├── public/                    # manifest、图标、Service Worker
│   ├── scripts/build-pwa.mjs
│   ├── node_modules/              # 本地依赖，已被 Git 忽略
│   └── dist/                      # 构建产物，已被 Git 忽略
├── scripts/
│   ├── dev.py                     # 同时启动 Vite / Uvicorn
│   └── build-experience.mjs        # 构建浏览器体验版
├── docs/
│   ├── API.md
│   ├── PROGRESS.md
│   ├── TEST_REPORT.md
│   └── INITIALIZATION_ACCEPTANCE.md
├── .venv/                         # 项目内 Python 虚拟环境，已被 Git 忽略
└── work/                          # 中间日志与临时文件，已被 Git 忽略
    └── acceptance/                # 本次检查日志和隔离的启动测试数据库
```

未发现项目级 AGENTS.md。版本库未跟踪依赖目录、SQLite 文件、运行日志或环境密钥文件。

## B. 已经完成的功能

- React + TypeScript + Vite 前端，TypeScript strict 开启。
- Python + FastAPI 后端，使用 Uvicorn 启动；提供 OpenAPI 文档。
- 手工录入及本项目消息接入 API，支持来源、原始编号、URL、发布时间。
- 原文持久化；没有原文编辑或删除 API；同来源编号幂等校验及冲突返回。
- 本地 rules-v1 解析：标题、摘要、类别、优先级及明确截止时间；不确定字段提示人工核对。
- 任务创建、编辑、待处理 / 进行中 / 已完成状态流转，通知与任务关联。
- 任务 → 通知 → 所有原始消息的来源追溯。
- 正文 NFC / 空白规范化后完全相同的通知合并，保留每条原文；没有模糊语义合并。
- 工作概览、原始消息、通知、任务、接入说明界面，搜索和任务筛选。
- SQLite 存储、UTC 时间存储、北京时间展示；可选本地访问令牌。
- PWA manifest、图标、应用壳缓存与安装事件处理；业务 API 不进入 Service Worker 缓存。
- 独立托管浏览器体验模式，IndexedDB 保存当前浏览器的体验记录。

## C. 尚未完成的功能

### 最终数据源范围

以下八类均属于后续目标，**当前均未实现专用连接器或自动采集**。任意填写来源标签不等于已接入或验证该平台。

| 数据源 | 当前状态 | 后续前提 |
|---|---|---|
| 西电学校官网 | 未接入 | 核对公开栏目、真实页面结构与访问规则 |
| 西电计算机科学与技术学院官网 | 未接入 | 核对公开栏目、真实页面结构与访问规则 |
| 学校微信公众号 | 未接入 | 明确授权及实际可用的内容获取方式 |
| 学校微信企业号 | 未接入 | 明确学校授权、账号角色与官方可用能力 |
| QQ 群 | 未接入 | 明确群消息处理授权和允许的导入方式 |
| 微信群 | 未接入 | 明确群消息处理授权和允许的导入方式 |
| 学在西电 | 未接入 | 获得真实授权及可验证的官方接口或导出材料 |
| XDYou | 未接入 | 获得真实授权及可验证的接口或导出材料 |

没有把“学在西电”当作 Canvas，也没有假设它们接口兼容。没有猜测上述平台接口。

### 其他待完成项

- 来源注册表、授权记录、采集任务调度、增量同步、重试和运行监控。
- PostgreSQL 实库兼容性测试；Alembic 等数据库迁移机制；备份与恢复验证。
- FastAPI 的远程托管，以及远程 React 与真实后端 / 数据库的完整部署联通。
- 多用户身份隔离与权限管理；当前为本地单用户应用，令牌是可选项。
- 服务端全文搜索 / 条件筛选与大数据量性能验证；当前界面逐页读完后本地筛选。
- 复杂通知解析及人工校正流程扩展；当前不解析附件、图片或相对日期。
- 真实浏览器端到端、移动设备及 PWA 安装 / 离线人工验收。
- GitHub Actions CI；完整的 Python 间接依赖锁定与部署依赖分层。

## D. 环境检查结果

| 检查项 | 实际结果 |
|---|---|
| 系统 Python / 项目 venv | 均为 3.12.14，venv 存在 |
| Node.js / npm | 24.19.0 / 11.9.0 |
| GNU Make | 4.4.1 |
| React / React DOM | 19.0.0 / 19.0.0 |
| TypeScript / Vite | 5.8.3 / 6.4.5 |
| Vitest / jsdom | 5.0.5 / 26.1.0 |
| FastAPI / Uvicorn | 0.115.12 / 0.34.2 |
| SQLAlchemy / psycopg | 2.0.40 / 3.2.6 |
| pytest / httpx | 8.3.5 / 0.28.1 |
| SQLite 库 | 3.53.1 |
| Python 依赖完整性 | pip check：No broken requirements found |
| Node 依赖完整性 | npm ls --depth=0 成功，无缺失 / 无效直接依赖 |
| 文档 | README、API、实施记录、历史测试报告齐全 |
| DATABASE_URL 覆盖 | 当前进程未设置，使用 backend/campusos.db |
| SQLite 实际文件 | 存在，PRAGMA integrity_check 返回 ok |
| SQLite 表 | messages、notifications、origins、tasks |
| PostgreSQL | 驱动已安装；未发现本地 postgres 可执行文件，未连接任何 PostgreSQL 实库 |
| 数据库迁移 | 启动时 create_all 创建缺失表，无版本化迁移 |
| CAMPUSOS_API_TOKEN | 当前未设置；默认服务仅绑定回环地址 |
| 项目 .env 文件 | 根目录、frontend、backend 均未发现 .env* 文件 |
| DeepSeek | 当前进程无名称含 DEEPSEEK 的环境变量；源码、依赖和启动脚本无模型调用或必需配置，命中仅为文档“不配置”说明 |
| Canvas 连接器 | 未发现 Canvas / Instructure / LTI 连接器、调用或配置 |

Canvas 检索说明：`frontend/package-lock.json` 中的 `canvas: ^3.0.0` 来自 jsdom 的 **optional peer dependency**，是 Node 绘图库声明，不是 Canvas 教学平台连接器；锁文件中没有 `node_modules/canvas` 安装条目。当前进程也没有名称含 CANVAS 的环境变量。因此不建议因同名而删除 jsdom 或测试依赖。

环境检查只输出相关变量名称及是否设置，未读取或输出凭据值；未检查私人账号数据。本轮未做新的 npm / Python 漏洞审计，依赖完整性通过不等于漏洞审计通过。

### 启动验证

- 原有开发服务：5173 前端、8000 后端、5173 的 `/api/health` 代理均返回 HTTP 200。
- 额外新启动临时 Uvicorn（18000）和 Vite（18173），前端首页、React 模块、后端健康检查均返回 HTTP 200。
- 18173 的 `/api/health` 按现有 Vite 配置转发到原有 8000 后端，返回 HTTP 200。
- 临时后端使用 `work/acceptance/startup-check.db`，成功创建四张业务表；通过命令进程局部环境指定，不修改系统全局变量或正式业务数据。
- 临时进程已停止，原有开发服务保留。
- 托管体验站点是静态 React + 浏览器 IndexedDB，与上述 FastAPI / SQLite 分开；本轮没有重新发布站点或测试真实浏览器。

## E. 本次测试结果

| 实际运行命令 / 检查 | 成功 | 失败 | 备注 |
|---|---:|---:|---|
| make test → pytest | 17 | 0 | 有 1 条弃用警告 |
| make test → Vitest | 14 | 0 | 5 个测试文件 |
| make build | 通过 | 0 | TypeScript + 普通 Vite 构建 + PWA 预缓存 |
| npm --prefix frontend run build:experience | 通过 | 0 | 托管模式构建 + PWA 预缓存 |
| 临时前后端启动及 HTTP 验证 | 通过 | 0 | 另保留原有运行服务 |
| SQLite 只读完整性检查 | 通过 | 0 | 未修改现有数据库 |

合计 **31 项已有自动化测试通过，0 项失败**。

pytest 警告：Starlette TestClient 使用 AnyIO BlockingPortal 弃用别名。pip check 另有全局缓存路径不可写提示并自动禁用缓存，检查仍成功；本轮未安装依赖。npm 输出的版本升级提示也不属于测试失败，未执行全局升级。

测试覆盖消息输入、幂等与冲突、原文重启持久化、规则解析、任务状态、来源追溯、去重、时区、分页、前端交互、错误展示、体验数据持久化及部分 PWA 行为。未验证真实校园数据源、PostgreSQL 实库或浏览器端到端行为。

原始日志位于项目内被忽略的 `work/acceptance/`：`tests.log`、`build-standard.log`、`build-experience.log`、`startup-backend.log`、`startup-frontend.log`、`startup-results.json`。

## F. 下一步推荐开发顺序（待确认后实施）

1. 确认八类来源的范围与授权边界，设计来源注册表、授权状态和接入状态；明确公开网页、用户授权导入及官方接口三种接入方式。
2. 加入数据库版本化迁移、PostgreSQL 实库回归及最小 CI，保证后续来源模型变更可追踪、可验证。
3. 优先接入学校官网与计算机科学与技术学院官网的公开通知；先核对真实栏目和访问规则，再实现增量采集、原文快照、追溯和去重。
4. 完善经授权的手工 / 文件导入，覆盖公众号、QQ 群、微信群通知，避免自动读取私人账号或使用未验证平台 API。
5. 取得真实授权和官方材料后，再逐一评估企业号、学在西电、XDYou 及公众号接口接入；无授权的来源保持禁用。
6. 在真实、合规样本基础上完善解析与人工确认，加入调度、重试、来源监控、权限隔离；最后完成完整后端远程部署及浏览器 / PWA 验收。

本轮到此结束，等待用户确认后再开始上述开发。未提交或推送本轮报告到 GitHub，业务源码保持受检提交状态。

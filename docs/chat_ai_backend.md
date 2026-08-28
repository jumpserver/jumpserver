# Chat AI 后端实现与 Lina 契约

## 仓库基线

- JumpServer 运行版本来自 `apps/jumpserver/const.py`，当前为 `2.0.0`；`pyproject.toml` 的包元数据版本为 `v4.0`，两者当前不一致，镜像构建会重写 `const.VERSION`。
- Python 要求 `>=3.14`，本地验证运行时为 Python 3.14.5。
- Django 5.2.13、Django REST framework 3.16.1、drf-spectacular 0.29.0。
- App 位于 `apps/<app_name>/`，通过 `apps.py` 注册，API 通常放在 `api/`，路由由 `urls/api_urls.py` 或 App 自有 URLConf 注册。
- DRF 认证顺序为 Chat AI 短期委托、Service Signature、Access Key Signature、Private Token、Bearer Access Token、OAuth2 和 Session。
- API 用户从 `request.user` 获取；Chat AI 从不接受客户端传入的 `user_id`。
- 组织上下文由 `OrgMiddleware` 建立，来源优先级为 query `oid`、`X-JMS-ORG` Header、`X-JMS-ORG` Cookie、Session `oid`。社区版固定使用 Default 组织。
- 默认 API 权限由 `RBACPermission` 调用 `request.user.has_perms()`；Chat AI 私有数据额外校验当前用户的组织 RoleBinding 和资源所有权。Agent 对 Core 的每次调用仍进入目标 ViewSet 的正常 RBAC、Serializer 和业务逻辑。
- Core API 在 `jumpserver.urls.resource_api` 下统一挂载到 `/api/v1/`。
- 分页为 `MaxLimitOffsetPagination`，使用 `limit`/`offset`，上限来自 `MAX_PAGE_SIZE`；异常由 `common_exception_handler` 转成 DRF `detail`/`code` 风格。
- OpenAPI 使用 drf-spectacular 的 `CustomSchemaGenerator` 和 `CustomAutoSchema`。文档地址为 `/api/swagger.json`、`/api/swagger.yaml`、`/api/docs/` 和 `/api/redoc/`。
- Chat AI Loader 直接以 `jumpserver.urls` 调用内部 Schema Generator，不解析 Swagger HTML；结果按 TTL 缓存并生成 SHA-256 Schema Hash。
- Core WSGI 为 `jumpserver.wsgi:application`；现有 ASGI 为 `jumpserver.asgi:application`，HTTP 最终进入 Channels 的 Django ASGI Application。
- Core Gunicorn 使用 `uvicorn.workers.UvicornWorker`，默认监听 8080；新增 AI Gunicorn 独立监听 8088。
- Docker Entrypoint 最终调用 `python jms start <service>`；`./jms start ai` 仅启动 AI 进程，不改变 `web`、`task` 或 `all` 的既有含义。
- 主 Core URLConf 保留 Chat AI 路由用于生成统一 OpenAPI 文档，但运行时权限只允许 AI URLConf 执行这些 ViewSet，避免模型与 SSE 占用普通 Core Web Worker。
- Celery App 为 `ops.celery`，自动发现 INSTALLED_APPS 的任务；实时 Chat/SSE 不进入 Celery。Chat AI 注册了过期 Approval、僵尸 AgentRun 和历史数据保留期限清理任务。
- Chat AI 使用统一的 OpenAI-compatible Provider 配置。管理页面通过 Core 代理查询 Provider 的 `/models`，模型密钥不会下发给浏览器或终端。

## API

所有接口必须登录，并携带可信组织上下文。个人会话接口只允许用户访问当前组织中属于自己的 Conversation 和 Approval；超级管理员通过独立审计接口只读查看当前组织的脱敏会话。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/chat-ai/conversations/` | 创建对话；请求可选 `title` 和内置 `assistant` |
| GET | `/api/v1/chat-ai/conversations/` | 当前用户、当前组织的对话列表 |
| GET | `/api/v1/chat-ai/conversations/{id}/` | 对话详情 |
| DELETE | `/api/v1/chat-ai/conversations/{id}/` | 删除对话；运行中返回 `409 CONVERSATION_BUSY` |
| GET | `/api/v1/chat-ai/conversations/{id}/messages/` | 消息列表，使用 Core 的 limit/offset 分页 |
| POST | `/api/v1/chat-ai/conversations/{id}/messages/stream/` | 请求 `{"content":"...","web_search":false}`，响应 `text/event-stream`；已有活动 Run 时返回 409 |
| POST | `/api/v1/chat-ai/conversations/{id}/messages/background/` | 创建后台消息，立即返回任务、Run 和 Message ID，完成后可发送站内信 |
| POST | `/api/v1/chat-ai/conversations/{id}/messages/{message_id}/regenerate/` | 基于原用户消息重新生成；不会把旧答案带入新上下文 |
| POST | `/api/v1/chat-ai/conversations/{id}/cancel/` | 停止当前生成，并取消该对话尚未确认的 Approval |
| POST | `/api/v1/chat-ai/transcriptions/` | 上传短音频并同步返回转写文字，不持久化音频和文字 |
| GET | `/api/v1/chat-ai/approvals/{id}/` | 获取安全预览，不返回签名、nonce 或原始凭证 |
| POST | `/api/v1/chat-ai/approvals/{id}/confirm/` | 校验并一次性执行写操作 |
| POST | `/api/v1/chat-ai/approvals/{id}/cancel/` | 取消写操作 |
| POST | `/api/v1/chat-ai/openapi/refresh/` | 超级管理员手动刷新 Registry |
| GET | `/api/v1/chat-ai/assistants/` | 返回内置通用、资产、会话审计和运维助手及其能力范围 |
| GET/POST | `/api/v1/chat-ai/scheduled-reports/` | 管理当前用户的只读定时诊断报告 |
| POST | `/api/v1/chat-ai/scheduled-reports/{id}/run/` | 立即排队执行一次定时报告 |
| GET | `/api/v1/chat-ai/stats/?days=30` | 超级管理员查看当前组织用量、Token、热门操作和定时任务统计 |
| GET | `/api/v1/chat-ai/audit/conversations/` | 超级管理员查看当前组织的会话审计元数据 |
| GET | `/api/v1/chat-ai/audit/conversations/{id}/` | 超级管理员只读查看脱敏后的用户与助手消息，并记录查看日志 |

创建对话响应示例：

```json
{
  "id": "uuid",
  "title": "",
  "model": "gpt-4o-mini",
  "status": "active",
  "date_created": "2026/07/14 17:00:00 +0800",
  "date_updated": "2026/07/14 17:00:00 +0800"
}
```

## 内置助手和诊断范围

Conversation 的 `assistant` 支持：

- `general`：通用问答和全部非敏感 Core API；绕过 operationId、Tag 和允许路径白名单，所有写操作仍需 Approval。
- `asset`：仅搜索资产、节点、平台、协议等只读 operationId。
- `session_audit`：仅搜索会话、命令、登录、操作、服务访问和工单审计 operationId。
- `ops`：仅搜索作业、任务、组件指标和终端状态 operationId。

通用助手不受 `CHAT_AI_ALLOWED_OPERATION_IDS`、`CHAT_AI_ALLOWED_TAGS` 和 `CHAT_AI_ALLOWED_PATHS` 限制；其他助手的固定范围仍与这些全局白名单取交集，不能借角色切换扩大权限。所有助手都继续受敏感路径、敏感参数、Method 策略、Core RBAC 和组织权限校验约束。默认允许通用助手执行查询及经 Approval 确认的创建、修改和删除操作。

Core API 调用完成后，结果卡片先在本次执行的内存中累计，在消息结束时一次性持久化到 Assistant Message 的 `result_cards`。卡片包含 `table`、`timeline`、`detail`、`metric`、`sources` 或仅供恢复用户可见过程的 `progress` 类型。SSE 的 `api_call_result` 同时返回 `presentation`，刷新对话后仍可从消息历史恢复过程与结构化结果；卡片构建或持久化异常不会改变回答和 Run 的最终状态。

## 后台执行和定时报告

后台消息通过 Celery 执行，不依赖浏览器持续保持 SSE。入队时 Run 为 `queued` 并持久化 Celery task ID，Worker 只有原子更新为 `running` 后才会执行；取消会同时落库和 revoke 队列任务，数据库状态是缓存失效后的最终兜底。Run 状态、正文、Token、API 审计和结果卡片与实时请求使用同一套数据结构；用户可继续通过 Conversation 的 `cancel` 接口请求停止。完成、失败或等待审批后，可使用现有站内信通知用户，通知异常不会改写任务执行结果。

后台消息和定时报告“立即运行”共享用户级接口频率、待执行数量和每日 Token 配额；立即运行会在入队事务内创建 Run，因此连续点击不会产生重复队列项。定时报告复用 JumpServer 的 Celery Beat `interval`/`crontab` 调度，注册名称使用完整 UUID；每次执行创建独立 Conversation，并在模型真正选定时记录实际模型，避免不同周期的上下文互相污染或历史模型为空。定时报告强制 `read_only=True` 且公网搜索默认关闭：即使全局白名单中存在写 operationId，也不会搜索或执行写操作，不会产生自动审批或无人值守变更。每个用户默认最多创建 10 个定时报告，由 `CHAT_AI_MAX_SCHEDULES_PER_USER` 控制。

会话审计使用独立接口，不放宽用户个人 Conversation 接口的所有权过滤。接口仅允许超级管理员访问当前组织的数据；列表不返回消息正文，详情只返回经过敏感信息脱敏的用户与助手消息。Tool 消息以及附件下载地址不会暴露，每次打开详情都会写入操作日志。

知识库/RAG 按当前产品决策不实现；保留的 `knowledge_search_*` SSE 事件不会发送。

确认响应示例：

```json
{
  "approval": {
    "id": "uuid",
    "operation_id": "assets_hosts_create",
    "method": "POST",
    "path": "/api/v1/assets/hosts/",
    "status": "confirmed",
    "preview": {},
    "result_summary": {}
  },
  "result": {
    "ok": true,
    "status_code": 201,
    "operation_id": "assets_hosts_create",
    "data": {}
  }
}
```

## 语音转写

请求使用 `multipart/form-data`：

```bash
curl -X POST https://example.com/api/v1/chat-ai/transcriptions/ \
  -H 'X-JMS-ORG: <org-id>' \
  -F 'file=@recording.webm' \
  -F 'language=zh'
```

`file` 必填，支持 `flac`、`m4a`、`mp3`、`mp4`、`mpeg`、`mpga`、`ogg`、`wav` 和 `webm`；`language` 可选，只接受 ISO-639 语言码，例如 `zh` 或 `en`。默认最大 10 MiB、最长 120 秒，每个用户默认每分钟 20 次、同时 1 路，全局同时 4 路。

时长校验依赖 `ffprobe`，正式镜像已安装；源码部署需要自行安装，或将 `CHAT_AI_STT_MAX_DURATION` 设为 `0` 关闭时长检查。

响应：

```json
{
  "text": "查询生产环境的主机资产",
  "language": "zh"
}
```

接口只做转写，不创建 Conversation 或 Message。Lina 可让用户检查、修改文字后，再调用现有消息 SSE 接口。上传先通过 `Content-Length`、实际文件大小和 `ffprobe` 时长检查，再以文件流交给 STT Provider，不再额外复制完整音频字节。Django 可能把较大的上传暂存到系统临时目录，但应用不会把原始音频或转写文本写入业务存储；请求结束后临时文件会关闭清理。

STT 使用 OpenAI Audio Transcriptions 协议。`CHAT_AI_STT_BASE_URL` 为空时复用 `CHAT_AI_BASE_URL`/`CHAT_AI_API_KEY`；显式设置 STT Base URL 后只使用 `CHAT_AI_STT_API_KEY`，为空时发送非敏感的本地占位凭据，因此不会把模型密钥泄露给新的服务地址。本地 Whisper 服务只需提供 OpenAI-compatible API。

## 联网搜索

联网搜索默认关闭。管理员启用后，Lina 输入框的 `+` 菜单会显示“联网搜索”；用户为本次提问选择该模式时，请求携带 `web_search=true`，Agent 才能调用 `search_web`。搜索结果作为不可信外部内容交给模型，最终回答要求使用 Markdown 链接标注来源。

当前支持：

- `tavily`：默认访问 `https://api.tavily.com/search`，必须配置独立的 Tavily API Key。
- `searxng`：访问自建实例的 `/search`，实例必须启用 JSON 响应；不会向该地址发送 Tavily API Key。

搜索服务拥有独立的 Base URL、API Key 和代理配置，不会复用或向搜索服务发送模型密钥。公网查询由当前一条原始用户问题直接生成，不采用模型在工具参数里生成的查询，也不读取附件、历史工具结果或 Core 响应来扩写；一旦本轮调用过 Core API，后续步骤会移除并拒绝 `search_web`。每次搜索最多返回 10 条结果，查询、来源、耗时和结果状态写入现有 `ApiCallAudit`；返回正文会做长度限制和敏感文本脱敏。

## SSE

每个事件使用 UTF-8 JSON：

```text
event: message_delta
data: {"content":"正在查询资产"}

```

模型长时间没有输出时，服务端默认每 15 秒发送一次 SSE 注释心跳 `: ping`。心跳不触发浏览器业务事件，只用于保持代理连接；流式正文每 2 秒或每新增 1024 字符增量落库。超过 10 分钟未更新的运行中 AgentRun 会由周期任务标记失败，避免会话永久占用。

机器可读 JSON Schema 见 `docs/chat_ai_sse_schema.json`。当前事件为：

- `message_start`：服务端 Message 和 AgentRun 已建立。
- `message_delta`：增量文本。
- `knowledge_search_start`、`knowledge_search_result`：保留给后续知识服务；第一阶段不会发送。
- `agent_plan`：本次执行边界和最大步数。
- `agent_progress`：模型生成的简短用户可见进度说明，不包含隐藏推理、技术标识或原始 API 数据。
- `web_search_start`、`web_search_result`：公网搜索状态和来源，携带模型生成的简短动作名；不会包含搜索服务凭证或完整网页正文。
- `api_search_start`、`api_search_result`：OpenAPI 搜索及候选 Operation，携带模型生成的简短动作名。
- `api_call_start`、`api_call_result`：Core API 调用过程，携带模型生成的简短动作名；不包含认证信息。
- `approval_required`：写操作安全预览和 Approval ID。
- `message_done`：`completed`、`awaiting_approval` 或 `cancelled`。
- `message_error`：安全错误码和可展示说明，不返回异常堆栈。

响应 Header：

```text
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache, no-transform
X-Accel-Buffering: no
Connection: keep-alive
```

客户端断开会触发 ASGI 取消，Provider HTTP 流会关闭，Message 和 AgentRun 会标记为 `cancelled`。主动停止使用 Conversation 的 `cancel` API。

## 认证、组织和委托

Lina 到 `jms_ai`：

- Session 模式：携带当前 Session Cookie、CSRF Cookie、`X-CSRFToken` 和 `X-JMS-ORG`。Cookie 名以运行时 `SESSION_COOKIE_NAME`、`CSRF_COOKIE_NAME` 为准。
- Token 模式：携带现有 `Authorization` 和 `X-JMS-ORG`；非 Session 认证不要求 CSRF。
- 浏览器跨域调用必须启用 credentials，并遵守当前 Core 的 CORS/CSRF 域配置。

`jms_ai` 不会把用户 Cookie、Token 或 Access Key Signature 重放给 Core。每次 Core 调用会生成最多 60 秒、一次性、HMAC 签名的 `X-JMS-AI-Delegation`，绑定：

```text
user_id
org_id
conversation_id
approval_id
allowed_operation_id
method
resolved_path
request_hash
issuer
audience
key_id
issued_at
expires_at
nonce
```

`request_hash` 覆盖 Method、Path、序列化后的 Query String 和原始请求 Body，防止票据被挪用于另一组参数。Core 的 `ChatAIDelegationAuthentication` 校验签名、issuer、audience、期限、组织、operationId、Method、Path、请求哈希和 Redis 一次性 nonce，恢复真实 `request.user` 后再执行正常 RBAC。

委托票据与 Approval 使用两个独立签名域；未显式配置时从 `SECRET_KEY` 分别派生不同密钥，也可用 `CHAT_AI_DELEGATION_SECRET` 和 `CHAT_AI_APPROVAL_SECRET` 完全解耦。`KEY_ID` 与 `VERIFY_KEYS` 支持保留旧钥完成平滑轮换。生产环境建议让 AI 到 Core 使用 HTTPS，并配置内部 CA 和 mTLS 客户端证书。

## Approval 和安全策略

- GET 默认允许且无需确认。
- POST、PUT、PATCH、DELETE 默认需要确认。
- DELETE 默认启用并要求确认，可通过 `CHAT_AI_METHOD_POLICIES` 关闭。
- Method 的 enabled、approval 和 risk_level 可通过 `CHAT_AI_METHOD_POLICIES` 收窄；高风险环境可继续关闭 DELETE。
- 默认屏蔽 Chat AI 自身、Password、Secret、Private Key、Access Key、Token、Credential 和账号备份相关路径。
- 还可用 Tag、operationId、Path 白名单及 Path 黑名单收窄范围。
- 模型只能提交 `operation_id + path_params + query_params + body`，不能提交 URL 或 Method。
- RequestBuilder 根据 OpenAPI 校验 Path、Query、Required、Enum、Array、Nullable、oneOf/anyOf、additionalProperties 和 JSON Body，并支持 form、spaceDelimited、pipeDelimited、deepObject Query 序列化。
- 模型首次提交的接口参数未通过 RequestBuilder 校验时，错误会作为工具结果返回给模型修正；单次参数错误不会直接中断整个回答。
- Approval 保存的请求不允许出现敏感字段；请求哈希由 Approval HMAC 票据覆盖。确认时会在事务内锁定记录并重新检查所有约束。
- 确认会恢复暂停点、执行已批准的单次 Core 调用并结束当前 AgentRun；确认响应直接携带结构化执行结果，不再开启第二条 SSE。
- 密码、Secret、Token、Cookie、私钥、API Key 等字段会被拒绝或脱敏。密码必须由 Lina 的独立安全表单直接提交给 Core。
- Sanitizer 同时应用于 API 请求审计、Core 响应、工具消息、Approval 预览和 SSE 结果。

## 错误码

普通 REST 错误沿用 Core 格式：

```json
{"detail": "...", "code": "permission_denied"}
```

| HTTP/SSE code | 含义 |
| --- | --- |
| `401 not_authenticated` | 未登录或委托票据无效 |
| `403 permission_denied` | 无当前组织 RoleBinding、资源不属于用户或 Core RBAC 拒绝 |
| `404 not_found` | Conversation/Approval 不存在，跨用户和跨组织也表现为 404 |
| `409 CONVERSATION_BUSY` | 对话仍有运行中或等待审批的 AgentRun |
| `MODEL_UNAVAILABLE` | 未启用、未配置或 Provider 不可用 |
| `MODEL_TIMEOUT` | 模型调用超时 |
| `400 invalid / invalid_audio` | 音频格式、语言码无效或上游无法识别 |
| `400 audio_too_long` | 音频超过配置时长 |
| `413 audio_file_too_large` | 音频超过配置大小 |
| `429 transcription_busy` | 用户或全局 STT 并发已满 |
| `429 speech_model_rate_limited` | 用户速率或语音 Provider 达到限流 |
| `503 audio_inspection_unavailable` | 启用时长限制但 ffprobe 不可用 |
| `503 transcription_capacity_unavailable` | STT 并发控制缓存不可用 |
| `503 speech_model_unavailable` | STT 未启用、未配置或鉴权失败 |
| `504 speech_model_timeout` | STT 调用超时 |
| `502 transcription_failed` | STT Provider 调用失败 |
| `AGENT_LIMIT_EXCEEDED` | 步数、API 次数或用户并发超限 |
| `POLICY_DENIED` | Operation 被策略禁止或含敏感字段 |
| `INVALID_AGENT_REQUEST` | 模型生成的参数不满足 OpenAPI |
| `message_done: cancelled` | 客户端主动停止；断开时持久化为 cancelled |
| `502 core_api_failed` | Approval 确认时 Core HTTP 执行异常 |

Core 返回 400、401、403、404、409、429 或 5xx 时，非审批 Agent 会收到结构化 `api_call_result`；Approval 确认会把 Approval 标记为 `failed` 并返回 Core 状态摘要。

## 运行和配置

推荐单独容器执行：

```bash
./jms start ai -w 2
```

等价命令：

```bash
cd apps
gunicorn jumpserver.ai_asgi:application \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 2 \
  --bind 0.0.0.0:8088 \
  --timeout 600
```

关键配置：

```yaml
CHAT_AI_ENABLED: true
CHAT_AI_BASE_URL: https://api.openai.com/v1
CHAT_AI_API_KEY: '<provider-api-key>'
CHAT_AI_PROXY: ''
CHAT_AI_MODEL: '<model-id>'
CHAT_AI_CORE_BASE_URL: https://jms_core:8080
CHAT_AI_CORE_TLS_VERIFY: true
CHAT_AI_CORE_CA_CERT: /etc/jumpserver/pki/ca.crt
CHAT_AI_CORE_CLIENT_CERT: /etc/jumpserver/pki/chat-ai.crt
CHAT_AI_CORE_CLIENT_KEY: /etc/jumpserver/pki/chat-ai.key
CHAT_AI_DELEGATION_KEY_ID: v1
CHAT_AI_DELEGATION_SECRET: '<independent-random-secret>'
CHAT_AI_APPROVAL_KEY_ID: v1
CHAT_AI_APPROVAL_SECRET: '<another-independent-random-secret>'
CHAT_AI_LISTEN_PORT: 8088
CHAT_AI_MODEL_TIMEOUT: 120
CHAT_AI_SSE_HEARTBEAT_INTERVAL: 15
CHAT_AI_PARTIAL_SAVE_INTERVAL: 2
CHAT_AI_PARTIAL_SAVE_CHARS: 1024
CHAT_AI_STALE_RUN_TIMEOUT: 600
CHAT_AI_QUEUED_RUN_TIMEOUT: 3600
CHAT_AI_STT_ENABLED: true
CHAT_AI_STT_BASE_URL: http://whisper:8000/v1
CHAT_AI_STT_API_KEY: ''
CHAT_AI_STT_MODEL: whisper-1
CHAT_AI_STT_TIMEOUT: 120
CHAT_AI_STT_MAX_FILE_SIZE: 10485760
CHAT_AI_STT_MAX_DURATION: 120
CHAT_AI_STT_FFPROBE_BIN: ffprobe
CHAT_AI_STT_RATE: 20/min
CHAT_AI_STT_MAX_CONCURRENCY: 1
CHAT_AI_STT_GLOBAL_CONCURRENCY: 4
CHAT_AI_IMAGE_MAX_COUNT: 4
CHAT_AI_IMAGE_MAX_FILE_SIZE: 5242880
CHAT_AI_IMAGE_MAX_TOTAL_SIZE: 10485760
CHAT_AI_FILE_MAX_COUNT: 4
CHAT_AI_FILE_MAX_FILE_SIZE: 10485760
CHAT_AI_FILE_MAX_TOTAL_SIZE: 20971520
CHAT_AI_FILE_MAX_EXTRACTED_CHARS: 40000
CHAT_AI_FILE_MAX_TOTAL_EXTRACTED_CHARS: 80000
CHAT_AI_WEB_SEARCH_ENABLED: true
CHAT_AI_WEB_SEARCH_PROVIDER: tavily
CHAT_AI_WEB_SEARCH_BASE_URL: https://api.tavily.com
CHAT_AI_WEB_SEARCH_API_KEY: '<web-search-api-key>'
CHAT_AI_WEB_SEARCH_PROXY: ''
CHAT_AI_WEB_SEARCH_TIMEOUT: 10
CHAT_AI_WEB_SEARCH_MAX_RESULTS: 5
CHAT_AI_WEB_SEARCH_MAX_CALLS: 3
CHAT_AI_WEB_SEARCH_MAX_RESPONSE_BYTES: 1048576
CHAT_AI_API_TIMEOUT: 15
CHAT_AI_MAX_CONCURRENCY: 2
CHAT_AI_MAX_STEPS: 15
CHAT_AI_MAX_API_CALLS: 30
CHAT_AI_MAX_CANDIDATES: 5
CHAT_AI_BACKGROUND_TASK_RATE: 10/min
CHAT_AI_BACKGROUND_MAX_PENDING_PER_USER: 5
CHAT_AI_BACKGROUND_TOKEN_RESERVATION: 8192
CHAT_AI_DAILY_TOKEN_LIMIT: 200000
CHAT_AI_MAX_SCHEDULES_PER_USER: 10
CHAT_AI_CONVERSATION_KEEP_DAYS: 180
CHAT_AI_ATTACHMENT_KEEP_DAYS: 30
CHAT_AI_RESULT_CARD_KEEP_DAYS: 90
CHAT_AI_AUDIT_KEEP_DAYS: 180
CHAT_AI_MAX_RESPONSE_BYTES: 1048576
CHAT_AI_APPROVAL_TTL: 600
CHAT_AI_SCHEMA_LOAD_ON_START: false
CHAT_AI_ALLOWED_OPERATION_IDS:
  - assets_platforms_list
  - assets_nodes_list
  - assets_hosts_list
  - assets_hosts_retrieve
  - assets_hosts_create
```

Chat AI 每天 02:00 分批清理超期数据。Conversation 默认保留 180 天，附件 30 天，结果卡片 90 天，Core API 调用审计、已结束 Approval 和已结束 AgentRun 保留 180 天；待执行、执行中和等待审批的数据不会被清理。任一 `*_KEEP_DAYS` 设置为 `0` 可单独关闭该类清理。

默认白名单用于资产、会话审计和运维助手的只读诊断范围；通用助手会绕过该白名单，并可执行全部非敏感 Core API。模型 Base URL、API Key、代理和模型名由统一的 Chat AI 系统设置管理；管理页面调用 `/api/v1/settings/chatai/models/` 动态发现模型，并通过 `/api/v1/settings/chatai/testing/` 验证模型的工具调用能力。

## 主要兼容性风险

- `const.VERSION` 与 Python 包元数据版本当前不一致，发布镜像应以构建后 `const.VERSION` 为准。
- 独立 AI 容器必须能通过 `CHAT_AI_CORE_BASE_URL` 访问 Core，且共享数据库、Redis、模型配置和相同的委托/Approval 签名配置；仅在使用派生默认密钥时才必须共享 `SECRET_KEY`。
- Schema 生成会遍历完整 Core API；首次加载成本高于命中缓存，失败时普通文本聊天仍可运行，但 API Tool 搜索为空。
- OpenAI-compatible Provider 必须支持 Chat Completions 流；不支持 `stream_options` 时会自动降级，但部分兼容服务可能不支持 tool calls。
- OpenAPI Cookie/Header 参数以及非 JSON Request Body 不会被 Agent 调用；当前只执行 Path、Query 和 JSON Body。
- SSE 必须运行在 ASGI Worker 后，并在反向代理关闭 buffering、配置足够的 read timeout。
- 知识服务/RAG 按当前产品决策不实现，仅保留 SSE 事件名称。

## 主要文件

- `apps/chat_ai/models.py`：Conversation、Message、AgentRun、ApiCallAudit、Approval 和 ScheduledReport。
- `apps/chat_ai/api/`：REST、SSE、取消、重新生成、后台任务、定时报告、统计、会话审计、审批和 Registry 刷新。
- `apps/chat_ai/assistants.py`：内置角色、提示约束和逐项 operationId 范围。
- `apps/chat_ai/presentation.py`：Core API 和联网来源的结构化结果卡片。
- `apps/chat_ai/agents/`：多步循环、Tool 调用、限额和取消。
- `apps/chat_ai/openapi/`：Schema Loader、Resolver、Registry 和搜索。
- `apps/chat_ai/executor/`：请求校验、Core HTTP 调用、审计和脱敏。
- `apps/chat_ai/web_search.py`：Tavily/SearXNG 搜索、结果归一化、限额和审计。
- `apps/chat_ai/file_extractor.py`：PDF、Office、文本和代码附件的正文提取与限额。
- `apps/chat_ai/providers/`：OpenAI-compatible 和 Fake Provider。
- `apps/chat_ai/policies/`：默认拒绝和配置化策略。
- `apps/chat_ai/authentication.py`、`delegation.py`：短期一次性用户委托。
- `apps/jumpserver/ai_asgi.py`、`ai_urls.py`、`settings/ai.py`：独立 AI ASGI 服务。
- `apps/chat_ai/migrations/`：独立数据表和 Approval 签名 key ID 迁移。

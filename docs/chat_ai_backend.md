# Chat AI：Kael 与 JumpServer Core 桥接

Chat AI 的运行时已经迁移到 Go 服务 Kael。Kael 负责对话编排、模型调用、流式响应和工具执行；
JumpServer Core 不再启动独立的 Python AI Runtime，也不再监听 8088。

Core 仍承担以下职责：

- 向 Kael 提供启用状态和模型 Provider 配置。
- 校验 Kael 代表最终用户调用 Core API 时携带的短期委托凭证，并继续执行正常的组织隔离和 RBAC。
- 通过内部 Runtime Store API 持久化 Kael 的 journal。问答数据因此仍保存在 JumpServer 数据库中。
- 将 Kael 上报的审计数据保存为独立的会话、消息审计表，提供列表、搜索和详情查询。
- 在 OpenAPI Schema 中提供工具调用所需的权限元数据。

## 服务关系

```text
Lina ── Chat AI 请求 ──> Kael
                         │
                         ├── 用户委托请求 ──> JumpServer Core API
                         │
                         └── journal ──> JumpServer Runtime Store

Lina ── AI 会话审计 ──> JumpServer Core ──> 审计会话 / 消息表
```

JumpServer 的 `web` 服务直接承载 Runtime Store 和被委托的业务 API。部署时不再启动独立的
Python Chat AI 进程或额外监听端口。

## AI 会话审计

审计台直接使用 Core 的只读接口：

- `GET /api/v1/chat-ai/audit/conversations/`：列表和分页；`search` 支持标题、用户姓名、用户名，沿用 Core 的搜索语法。
- `GET /api/v1/chat-ai/audit/conversations/{id}/`：会话详情；访问记录写入 Core 操作日志。
- `OPTIONS /api/v1/chat-ai/audit/conversations/`：列表及搜索元数据。

这些接口使用 `chat_ai.view_auditconversation` 权限，并严格按当前组织隔离。内置系统审计员和组织
审计员拥有该只读权限，自定义角色可在审计台权限树中单独授权；普通用户不会自动获得审计权限。
前端菜单、列表和详情使用同一权限。查询不访问 Kael，也不要求开启 AI 功能，
因此可以在 Kael 停机或禁用 AI 后查询已经写入的历史。

会话和消息审计模型继承 `OrgModelMixin`，通过组织感知的 manager 隔离查询，并保留 Kael 上报的
记录 ID 和时间。消息的 `org_id` 由所属会话确定，不接受单独指定。消息表的
`(conversation_id, role, date_created)` 联合索引用于列表中的消息数、提问数和最后提问时间统计；
会话表保留 `(org_id, date_updated)` 索引。

Kael 在签名的 Runtime Store `record` JSON envelope 中添加可选的 `audit` 对象，包含
`version: 1`、`conversations` 和 `messages` 数组。原有 `payload` 仍是 Core 不解析的运行时数据；
`audit` 是单独校验的 JSON 数据协议，并受整个 record 的提交 HMAC 保护。Core 在同一个数据库事务中
提交 journal 和审计数据，按稳定的会话、消息 ID 更新，不接受资源所属组织、用户或会话的变更。
回复在完成、失败或取消时上报；问题在提交时上报。Core 对保存的标题、正文和错误文本进行脱敏。

普通会话和终端 AI 都上报审计记录。Kael 启动时分批补录当前仍保留的历史，重复启动或中断重试不会
生成重复审计数据。终端本地历史或运行时会话的删除不会级联删除 Core 审计记录；升级前已经被清理的
历史无法通过补录恢复。历史核对会增加 Kael 启动耗时，取决于保留的数据量。

升级顺序：先部署 Core 并执行 `chat_ai.0002_conversation_audit` 迁移，创建审计表和查看权限，
再部署 Kael 完成补录，最后更新 Lina。新 Kael 要求写入响应包含 `audit_version: 1`，
防止连接到不支持审计写入的旧 Core。
审计标题、用户姓名/用户名、消息正文/错误和 journal `record` 使用 `UnicodeCharField` /
`UnicodeTextField`，在 MySQL/MariaDB 上默认声明 `utf8mb4_general_ci`，允许保存 emoji 等四字节字符；
其他数据库沿用原生字段的默认行为。`0002` 通过 `CreateModel` 创建审计表，并通过 `AlterField`
更新 journal 字段，字符集要求与模型定义一起维护。
已经执行过旧版 `0002` 的环境需单独同步这些列，修改迁移文件后再次运行 `migrate` 不会重做已应用的迁移。
写入复用既有提交 ID、revision 校验和有限重试；Core 无法确认持久化时，Kael 不会把该事务作为成功
提交返回。旧 Kael 的 `/kael/api/v1/admin/audit/conversations` 读接口已移除。

## Core 配置

Core 保留以下设置：

| 设置 | 用途 |
| --- | --- |
| `CHAT_AI_ENABLED` | 是否向客户端和组件启用 Chat AI |
| `CHAT_AI_PROVIDER` | Kael 使用的 Provider 类型 |
| `CHAT_AI_BASE_URL` | OpenAI-compatible Provider 地址 |
| `CHAT_AI_API_KEY` | Provider 凭据 |
| `CHAT_AI_PROXY` | Provider HTTP 代理 |
| `CHAT_AI_MODEL` | 默认模型 ID |
| `CHAT_AI_MODEL_TIMEOUT` | Core 管理页发现和测试模型时的超时 |
| `CHAT_AI_DELEGATION_ISSUER` | 用户委托票据签发者 |
| `CHAT_AI_DELEGATION_AUDIENCE` | 用户委托票据受众 |
| `CHAT_AI_DELEGATION_KEY_ID` | 当前委托签名密钥 ID |
| `CHAT_AI_DELEGATION_SECRET` | 当前委托签名密钥；为空时从 `SECRET_KEY` 派生 |
| `CHAT_AI_DELEGATION_VERIFY_KEYS` | 密钥轮换期间仍可验证的旧密钥映射 |

Terminal 配置会把启用状态和 Provider 配置提供给 Kael。管理页面仍通过
`POST /api/v1/settings/chatai/models/` 发现模型，通过
`POST /api/v1/settings/chatai/testing/` 验证所选模型与 Kael 的 Responses API 兼容性。
测试不使用 Chat Completions，也不自动重试，按两轮流式请求验证：

1. 模型通过 `response.output_item.done` 返回指定的 `function_call`，名称、`call_id`
   和 JSON 参数有效；流必须以成功的 `response.completed` 事件完成。
2. 保留第一轮的完整输出（包括 reasoning），以匹配的 `call_id` 回传
   `function_call_output`，其中包含临时生成的随机 nonce。模型必须通过文本增量返回
   该 nonce，且增量与最终内容一致，以确认模型实际接收并使用了工具结果。

普通 JSON 响应、截断或失败的流、无效工具调用、错误的工具结果回传均不能通过测试。
测试成功保留 `msg`、`model`、`tool_calls` 字段，并返回 `responses`、`streaming`、
`tool_result` 为 `true`。这些检查验证模型端点的协议能力，不替代 Kael 运行环境的端到端检查。

## 用户委托与 Core RBAC

Kael 调用需要最终用户权限的 Core API 时，携带：

- `X-JMS-AI-Delegation`：短期 HMAC 委托票据。
- `X-JMS-AI-Operation`：本次调用的 OpenAPI operation ID。
- `X-JMS-ORG`：当前组织 ID。

票据绑定用户、组织、operation ID、HTTP Method、Path、Query String 和原始 Body，最长有效期为
60 秒，并包含一次性 nonce。Core 验证 issuer、audience、key ID、签名、有效期、请求哈希和
nonce 后恢复真实用户；随后请求仍进入目标 API 原有的组织隔离、RBAC、Serializer 和业务逻辑。
委托认证不会授予用户原本没有的权限。

`CHAT_AI_DELEGATION_VERIFY_KEYS` 用于平滑轮换密钥。新票据使用
`CHAT_AI_DELEGATION_KEY_ID` 和 `CHAT_AI_DELEGATION_SECRET`，旧票据只在对应 key ID 仍位于
verify keys 且票据尚未过期时有效。

## Runtime Store API

Kael 使用不进入公开 OpenAPI 文档的内部接口：

```text
GET  /api/v1/chat-ai/runtime-store/
POST /api/v1/chat-ai/runtime-store/
```

接口使用 Access Key HTTP Signature 认证。认证用户必须是服务账号，并绑定到
`type=kael` 的 Terminal；普通用户、其他组件服务账号和用户委托票据都不能访问。

Runtime Store 是全局有序、只追加的 journal。Core 将 `record` 的运行时 payload 作为不透明数据保存，但会验证
JSONL envelope、payload checksum、提交完整性和 revision。单条 record 上限为 64 MiB。

### 读取

读取请求必须提供本次请求生成的 UUID nonce：

```text
GET /api/v1/chat-ai/runtime-store/?nonce=<uuid>&after=0&limit=1000
```

- `after` 默认为 `0`，表示调用方已经持久化的 revision。
- `limit` 默认为 `1000`，范围为 1 到 1000。
- 若 `after` 早于最新 snapshot，响应会从该 snapshot 开始。
- 单页 record 总量达到 64 MiB 时，即使未达到 `limit` 也会截断并返回 `has_more=true`。

响应结构：

```json
{
  "nonce": "<uuid>",
  "revision": 12,
  "results": [
    {
      "revision": 12,
      "commit_id": "<uuid>",
      "snapshot": false,
      "record": "<jsonl-record>"
    }
  ],
  "has_more": false,
  "receipt": "<hmac-sha256>"
}
```

`receipt` 使用当前请求 Access Key 的 secret，对以下无末尾换行的 canonical 内容执行
HMAC-SHA256；每个 result 按响应顺序追加最后四项：

```text
kael-runtime-store-page-v1
default
<nonce>
<after>
<limit>
<head_revision>
<0|1 has_more>
<result_count>
<revision>
<commit_id>
<0|1 snapshot>
<sha256(record)>
```

响应带有 `Cache-Control: no-store`。调用方应验证 receipt，并在 `has_more=true` 时使用本页
最后一条 record 的 revision 继续读取。

### 写入

```json
{
  "commit_id": "<uuid>",
  "expected_revision": 11,
  "snapshot": false,
  "record": "<jsonl-record>",
  "integrity": "<hmac-sha256>"
}
```

`record` 必须是恰好一行的 JSON，包含 `version`、`created_at`、`payload`、`checksum`，
以及可选的 `audit` 对象。当前 `version` 为 `1`；`payload` 是 Base64，`checksum` 是 payload 解码后字节的
SHA-256。

`integrity` 使用当前请求 Access Key 的 secret 签名：

```text
kael-runtime-store-commit-v1
default
<commit_id>
<expected_revision>
<0|1 snapshot>
<sha256(record)>
```

Core 在事务内锁定 revision 并执行 CAS。成功返回 HTTP 201：

```json
{
  "revision": 12,
  "commit_id": "<uuid>",
  "receipt": "<hmac-sha256>"
}
```

成功 receipt 的 canonical 内容为：

```text
kael-runtime-store-receipt-v1
default
<commit_id>
<expected_revision>
<revision>
<0|1 snapshot>
<sha256(record)>
```

revision 不匹配时返回 HTTP 409 和 `runtime_store_revision_conflict`。`commit_id` 支持网络失败后的
幂等重试，但仅当 revision、snapshot、record 均相同且该提交仍是当前 head 时返回相同结果。
写入 snapshot 时，Core 在同一事务中保存新 snapshot，并删除它之前的 journal records。

## 数据与运维边界

- Runtime Store 表为 `chat_ai_runtime_store` 和 `chat_ai_runtime_store_record`。
- Core 不解析 Kael payload 的业务语义；恢复、压缩和对话状态演进由 Kael 负责。
- Access Key 轮换不会重写历史 record；读取和写入 receipt 始终使用当前请求的 Access Key。
- 反向代理的请求体限制必须高于 64 MiB，以容纳 record 外层 JSON 和字符串转义开销。
- Runtime Store API 只能在 Core 的 `/api/v1/chat-ai/` 路由下访问，不应单独暴露服务端口。

Chat AI 尚未发布，因此迁移历史已经收敛为只创建 Runtime Store 的 `0001_initial`，不提供旧
Python Runtime 表的数据迁移或兼容。使用过旧开发分支的环境需要重新初始化开发数据库后再启动
Core；全新环境只会创建上述两张 Runtime Store 表。

主要实现位置：

- `apps/chat_ai/api/runtime_store.py`：认证、签名校验、CAS、分页和 receipt。
- `apps/chat_ai/serializers.py`：Runtime Store 请求校验、响应序列化，以及会话审计的输入输出序列化。
- `apps/chat_ai/const.py`、`apps/chat_ai/utils.py`：journal 协议常量和共享 JSON 校验函数。
- `apps/chat_ai/models.py`：Runtime Store head 与 journal record。
- `apps/chat_ai/authentication.py`：用户委托认证。
- `apps/chat_ai/delegation.py`、`apps/chat_ai/signing.py`：委托校验和密钥轮换。
- `apps/terminal/models/component/terminal.py`：下发 Kael 所需配置。

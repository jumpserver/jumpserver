# Chat AI：Kael 与 JumpServer Core 桥接

Chat AI 的运行时已经迁移到 Go 服务 Kael。Kael 负责对话编排、模型调用、流式响应和工具执行；
JumpServer Core 不再启动独立的 Python AI Runtime，也不再监听 8088。

Core 仍承担以下职责：

- 向 Kael 提供启用状态和模型 Provider 配置。
- 校验 Kael 代表最终用户调用 Core API 时携带的短期委托凭证，并继续执行正常的组织隔离和 RBAC。
- 通过内部 Runtime Store API 持久化 Kael 的 journal。问答数据因此仍保存在 JumpServer 数据库中。
- 在 OpenAPI Schema 中提供工具调用所需的权限元数据。

## 服务关系

```text
Lina ── Chat AI 请求 ──> Kael
                         │
                         ├── 用户委托请求 ──> JumpServer Core API
                         │
                         └── journal ──> JumpServer Runtime Store
```

JumpServer 的 `web` 服务直接承载 Runtime Store 和被委托的业务 API。部署时不再启动独立的
Python Chat AI 进程或额外监听端口。

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
`POST /api/v1/settings/chatai/testing/` 验证所选模型的工具调用能力。

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

Runtime Store 是全局有序、只追加的 journal。Core 将 `record` 作为不透明字符串保存，但会验证
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

`record` 必须是恰好一行的 JSON，且只能包含 `version`、`created_at`、`payload` 和
`checksum`。当前 `version` 为 `1`；`payload` 是 Base64，`checksum` 是 payload 解码后字节的
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

- `apps/chat_ai/api/runtime_store.py`：认证、校验、CAS、分页和 receipt。
- `apps/chat_ai/models.py`：Runtime Store head 与 journal record。
- `apps/chat_ai/authentication.py`：用户委托认证。
- `apps/chat_ai/delegation.py`、`apps/chat_ai/signing.py`：委托校验和密钥轮换。
- `apps/terminal/models/component/terminal.py`：下发 Kael 所需配置。

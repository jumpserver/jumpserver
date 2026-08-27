# 应用接入凭据服务

应用使用“应用管理”中 Integration Application 的“应用 ID + Secret”调用凭据服务。凭据策略必须绑定该应用；一个应用不能读取或管理其他应用的策略与租约。

示例客户端 [`client.py`](./client.py) 只使用 Python 标准库，覆盖固定凭据读取、临时凭据申请、租约查询、续租和主动撤销。

部署和发布前请按 [`TESTING.zh-hans.md`](./TESTING.zh-hans.md) 完成管理页面、真实资产、故障恢复和安全负向测试。

## 准备

1. 在“应用管理”创建或选择应用，保存应用 ID 和 Secret，并确认应用处于启用状态。
2. 将调用方 IP 加入应用允许的 IP 范围。
3. 在应用详情的“凭据策略”页签创建策略，记录策略 ID。
4. 调用方和 JumpServer 都使用 NTP 校时；生产环境只通过 HTTPS 调用。

```bash
export JMS_URL='https://jumpserver.example.com'
export JMS_APP_ID='00000000-0000-0000-0000-000000000001'
export JMS_APP_SECRET='replace-with-application-secret'
export JMS_ORG_ID='00000000-0000-0000-0000-000000000002'

python3 apps/accounts/demos/credential_service/client.py self-test
```

`JMS_URL` 可以包含反向代理路径前缀，但应直接填写最终 HTTPS 地址；示例客户端为避免签名凭据被转发而拒绝 HTTP 重定向。请求超时默认是 35 秒，可通过 `JMS_TIMEOUT` 调整；临时凭据签发在服务端最多等待 30 秒，因此客户端超时不能低于 30 秒。

## 接口与示例

### 读取固定轮换账号的最新凭据

```http
GET /api/v1/accounts/credential-service/policies/{policy_id}/credential/
```

```bash
python3 apps/accounts/demos/credential_service/client.py fixed "$POLICY_ID"
```

成功返回 `username`、`secret`、`secret_type`、`version`、`rotated_at` 和 `next_rotation_at`。响应带有 `ETag`；后续请求可以携带 `If-None-Match`，未变化时返回 `304`：

```bash
python3 apps/accounts/demos/credential_service/client.py fixed \
  "$POLICY_ID" --etag '"credential-policy-..."'
```

应用不得依赖历史版本。策略停用、轮换中或状态不确定时，接口不会返回当前密码。

### 申请临时凭据

```http
POST /api/v1/accounts/credential-service/policies/{policy_id}/credentials/
```

该请求没有请求体。服务端同步等待创建结果，成功后直接返回 `username`、`secret`、`lease_id`、`ttl`、`expires_at`、`max_expires_at` 和 `renewable`。

```bash
export REQUEST_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
python3 apps/accounts/demos/credential_service/client.py issue \
  "$POLICY_ID" --idempotency-key "$REQUEST_ID"
```

`Idempotency-Key` 是调用应用生成的可选键，最长 128 个字符。同一策略中重复提交同一个键会在可重放窗口内返回同一次签发结果，密码最多可重读 5 分钟。发生连接中断、网关超时等“不确定请求是否到达”的情况时，必须复用原键；每次重试仍需生成新的 Nonce、Date 和签名。收到明确的签发失败后，应等待清理完成并使用新键重新申请。

### 查询租约

```http
GET /api/v1/accounts/credential-service/leases/{lease_id}/
```

```bash
python3 apps/accounts/demos/credential_service/client.py lease "$LEASE_ID"
```

租约查询只返回用户名、状态、TTL 和审计字段，不会再次返回密码。

### 续租

```http
POST /api/v1/accounts/credential-service/leases/{lease_id}/renew/
Content-Type: application/json

{"increment":600}
```

```bash
python3 apps/accounts/demos/credential_service/client.py renew \
  "$LEASE_ID" --increment 600
```

省略 `increment` 时按策略默认 TTL 延长，但绝不会超过 `max_expires_at`。只有 `active` 且未过期、未达到最大生命周期的租约可以续租。

### 主动撤销

```http
DELETE /api/v1/accounts/credential-service/leases/{lease_id}/
```

```bash
python3 apps/accounts/demos/credential_service/client.py revoke "$LEASE_ID"
```

首次通常返回 `202 revoking`。继续查询租约，直到状态变为 `revoked` 或 `expired`。撤销完成后，JumpServer 删除目标端临时账号；即使目标端删除失败，本地 `Account` 也会删除，失败原因保留在租约审计中。

## HTTP Signature 契约

所有凭据服务请求使用 HMAC-SHA256。以下字段必须存在且参与签名：

| 字段 | 要求 |
| --- | --- |
| `(request-target)` | 小写 HTTP 方法、完整路径和原始查询串，例如 `get /api/v1/.../credential/` |
| `Date` | RFC 7231 GMT 时间，与 JumpServer 时间偏差不超过 5 分钟 |
| `X-JMS-ORG` | Integration Application 所属组织 ID，必须完全一致 |
| `X-Source` | 固定为 `jms-pam` |
| `X-JMS-Nonce` | 每次请求唯一的 16～128 字符随机值；服务端 10 分钟内拒绝重放 |
| `Digest` | 有请求体时必填并签名，值为原始请求体字节的 `SHA-256` Base64 |
| `Idempotency-Key` | 携带时必须参与签名；仅用于临时凭据申请 |

签名字符串按 `headers` 声明顺序逐行拼接，例如续租请求：

```text
(request-target): post /api/v1/accounts/credential-service/leases/{lease_id}/renew/
date: Wed, 26 Aug 2026 01:02:03 GMT
x-jms-org: 00000000-0000-0000-0000-000000000002
x-source: jms-pam
x-jms-nonce: 0123456789abcdef
digest: SHA-256=...
```

然后计算 `Base64(HMAC-SHA256(application_secret, signing_string))`，并发送：

```http
Authorization: Signature keyId="{application_id}",algorithm="hmac-sha256",headers="(request-target) date x-jms-org x-source x-jms-nonce digest",signature="..."
```

`Digest` 必须针对最终发送的同一份字节计算；签名后不能重新格式化 JSON。不要复用 Nonce，也不要把 Secret、密码或完整 Authorization 写入日志。

## 错误处理

凭据策略的业务状态错误返回：

```json
{"code":"CREDENTIAL_POLICY_DISABLED","detail":"Credential policy is not enabled"}
```

签名认证失败返回 `401 {"detail":"Invalid signature."}`；请求字段校验失败沿用 DRF 的字段错误对象，例如 `{"increment":["..."]}`。客户端应先按 HTTP 状态分类，再读取可选的 `code` 和 `detail`，不能假定所有错误都有统一 JSON 结构。

| HTTP 状态 | 处理建议 |
| --- | --- |
| `400` | 请求体或字段不正确；修正请求，不自动重试 |
| `401` | 检查应用 ID/Secret、Digest、签名、时钟、Nonce、来源头和 IP 白名单 |
| `403` | 策略已停用或系统禁止查看密码；立即停止新连接读取/签发 |
| `404` | ID 不存在，或资源不属于当前应用/组织；不要猜测其他 ID |
| `409` | 策略类型、租约状态、配额或幂等重放窗口冲突；先读取当前状态再决定 |
| `502/503/504` | 平台不可达、轮换中或执行超时；指数退避并设置总重试上限 |

网络错误表示结果未知：临时凭据申请必须使用相同 `Idempotency-Key` 重试。对服务端明确返回的错误，不要无限重试；尤其不能用不同幂等键并发申请，否则会创建多个租约。

## 应用连接池切换

固定轮换凭据建议按以下顺序刷新：

1. 定时读取并使用 `ETag` 判断版本是否变化。
2. 收到新版本后创建新连接池，使用新凭据完成健康检查。
3. 原子切换业务流量到新连接池。
4. 等待旧请求排空后关闭旧连接池；不要把新密码直接写入仍存活的旧连接对象。

临时凭据建议让一个连接池对应一个租约：在 `expires_at` 前预留充足时间续租；达到 `max_expires_at` 或续租失败时，先申请新租约并完成上述连接池切换，再主动撤销旧租约。应用正常退出时也应撤销自己的租约。密码只保存在必要的进程内存中，不落盘、不进入缓存、指标、异常栈或日志。

## 上线前检查

- 使用固定测试策略确认 `200 -> ETag -> 304`，并在一次手动轮换后确认版本和密码变化。
- 使用临时策略确认申请、查询、续租、撤销完整闭环，目标端账号与 JumpServer `Account` 状态一致。
- 使用同一个 `Idempotency-Key` 模拟网络重试，确认只产生一个租约；使用相同 Nonce 重放，确认返回 `401`。
- 将客户端时间分别偏移 6 分钟并确认签名被拒绝，恢复 NTP 后成功。
- 停用策略，确认新的固定密码读取、临时凭据申请和续租立即被拒绝，已有租约进入撤销流程。
- 确认反向代理不改写签名使用的路径、查询串、Date、Digest、Nonce 和 Authorization。
- 检查应用日志、APM、请求抓包和告警，确保没有密码或应用 Secret。

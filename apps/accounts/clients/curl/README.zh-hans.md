# cURL — 使用指南

本目录提供旧 account-secret API 的 HTTP 签名调试脚本。应用接入请使用 Python、Go、Java 或 Node.js SDK。

## 环境要求

- Bash / cURL / OpenSSL / base64
- `demo.sh`

脚本需要 Bash、cURL、OpenSSL 和 base64。替换脚本中的 ASSET 和 ACCOUNT，并确保签名查询参数与 cURL 实际发送的编码完全一致。

## 配置与运行

在应用管理中创建应用并授权目标资产账号。填写下方端点、应用 AK/SK 和组织 ID，运行前将所有占位符替换为真实值。

```bash
cd apps/accounts/clients/curl
export API_URL='https://jumpserver.example.com'
export API_KEY_ID='<app-id>'
export API_KEY_SECRET='<app-secret>'
export ORG_ID='<org-id>'

bash demo.sh
```

示例默认查询资产 ubuntu_docker 和账号 root，请在代码中改为实际授权的名称。上面的命令从仓库根目录开始执行。示例输出包含密码，不要发送到应用日志。

## 请求与响应

```http
GET /api/v1/accounts/integration-applications/account-secret/?asset=ubuntu_docker&account=root
```

```json
{"id":"<app-id>","secret":"<account-secret>"}
```

响应 id 表示应用身份，不表示账号版本；secret 为 null 时可能受服务端密码查看设置限制。这些示例不接收凭据事件、不上报生效版本，也不执行应用指令。

## 排查问题

401 时检查 AK/SK、组织、主机时间和签名 URL；403 时检查应用状态与账号授权；400 时检查资产/账号选择参数及 URL 编码。不要记录密码或 Authorization 请求头，资产名和账号名应与应用获授权资源一致。

## 凭据策略接入

下方签名细节和协议表供调试参考。凭据策略接入通过 SDK 方法完成，也可通过 Go jms-pam-agent 的 JSON 文件、EnvironmentFile 或 Unix Socket 接入。

| HTTP | API | JSON / query |
| --- | --- | --- |
| GET | `/api/v1/accounts/credential-client/credential/` | `instance_id`, `key` / `account_id` |
| POST | `/api/v1/accounts/credential-client/confirm/` | `instance_id`, `key`, `revision`, `account_id` |
| GET | `/api/v1/accounts/credential-client/commands/` | `instance_id` |
| POST | `/api/v1/accounts/credential-client/command-result/` | `instance_id`, `command_id`, `status`, `error_code` |
| WebSocket | `/ws/accounts/credential-events/` | `instance_id` |

按下方请求头顺序计算 HMAC-SHA256 签名。request-target 包含编码后的路径与查询参数，Digest 使用实际请求体的 SHA-256，X-JMS-Request-ID 使用唯一 UUID，Date 使用 HTTP UTC 时间；设置 X-JMS-Client-Version、X-JMS-Protocol-Version: 1 和 SDK 的 X-JMS-Config-Schema-Version: 0。API 与 WebSocket 均使用应用 AK/SK 和稳定、唯一的 instance_id，每次请求和重连重新生成签名。

```text
(request-target) accept date digest x-jms-request-id x-jms-org
x-jms-client-version x-jms-protocol-version x-jms-config-schema-version
```

交替轮换需要先验证真实连接、切换应用连接池并释放旧连接，再确认准确的 key、revision 和 account_id。凭据变更订阅无需确认，连接验证失败时不得确认。

received 回执只表示已读取事件。处理带 event_id 的业务事件前，在同一 WebSocket 发送 received；snapshot 和 pong 无需回执。每次连接或重连都对齐快照，处理 credential.updated，并响应撤销授权和配置变化。

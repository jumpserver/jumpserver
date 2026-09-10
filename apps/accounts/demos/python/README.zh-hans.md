# JumpServer PAM Python SDK 与 Agent

## Python SDK

环境要求：Python 3.9 及以上。

### URL 安装

在应用详情的「客户端接入」中生成配置，复制安装命令执行。以下为本机 JumpServer 地址示例：

```bash
python3 -m pip install --index-url https://pypi.org/simple http://127.0.0.1:8080/api/v1/accounts/python-sdk/
```

SDK 源码从 JumpServer 下载；setuptools 等构建工具以及 requests 等运行依赖从官方 PyPI 下载。安装时需能访问 JumpServer 和软件源，不需要本地 `packages` 目录。请使用应用实际运行的 Python 或虚拟环境；在其他机器安装时，用页面生成的、该主机可访问的 JumpServer 地址，不能沿用 127.0.0.1。

如果出现 `installing build dependencies` 和 `No matching distribution found for setuptools`，使用 `pip -v` 查看软件源访问错误。清华镜像返回 403 时不代表 setuptools 版本不存在；上述命令显式指定官方源，仅影响本次安装，不改全局 pip 配置。企业限制公网时请将 `--index-url` 替换为可用且提供这些依赖的内部源，不要用 `--no-deps` 或 `--no-build-isolation` 掩盖缺失依赖。

### 应用接入

在应用详情的「客户端接入」中创建配置、选择应用凭据，再下载 `jms-pam.json`。文件已包含地址、应用 ID、密钥、组织 ID 和接入配置 ID，不需要另找参数。请按敏感文件保管。

```python
from jms_pam import JumpServerPAMClient

client = JumpServerPAMClient.from_config('jms-pam.json')

credential = client.get_credential('cred-pg-main')

new_pool = create_pool(
    username=credential.username,
    password=credential.secret,
)
new_pool.check_connection()
old_pool.close()

client.confirm_applied(credential)
```

应用运行期间需要定期调用 `get_credential()` 获取最新版本。取到凭据不代表应用已经使用它；成功建立新连接并释放旧连接后，才调用 `confirm_applied()`。SDK 自动每 30 秒上报心跳。

每个独立使用凭据/连接池的业务进程都必须显式配置稳定、唯一的实例标识（配置文件的 `instance_id` 或环境变量）。SDK 不再默认使用主机名；同主机不同 worker、不同主机之间不能复用标识，重启同一逻辑实例时保持原标识。请在进程 fork 后分别创建 SDK 客户端。本版不检测同名并发会话，唯一性由部署配置保证：

```bash
export JMS_PAM_INSTANCE_ID=order-service-node-1
```

首次调用 `from_config()` 前设置该环境变量；未配置、超过 128 字符或包含首尾空白时，SDK 会明确拒绝启动。

## Linux Agent

Agent 支持 Python 3、Linux 和 systemd。应用从 `/etc/jumpserver-pam/credentials.json` 读取当前账号，Agent 本地接口只监听 `127.0.0.1:8081`，不提供取密接口，也不使用本地认证。

页面生成的 Agent 命令会创建虚拟环境，从 JumpServer URL 安装 SDK/Agent，并连接 JumpServer 注册；构建和运行依赖使用命令中指定的软件源。注册材料有效期为 10 分钟且只能使用一次。已安装 Agent 时，注册命令如下（请使用安装所在虚拟环境的 `jms-pam-agent`）：

```bash
sudo jms-pam-agent install \
  --endpoint https://jms.example.com \
  --token 一次性注册令牌 \
  --instance-id order-service-node-1 \
  --credential cred-pg-main \
  --app-user order-service
```

Agent 每 30 秒检查凭据版本并原子更新配置文件。应用重载、验证新连接并释放旧连接后执行：

```bash
jms-pam-agent confirm cred-pg-main --revision 2
```

凭据文件示例：

```json
{
  "cred-pg-main": {
    "key": "cred-pg-main",
    "revision": 2,
    "asset": "pg-prod-01",
    "address": "10.0.0.10",
    "account": "account-b",
    "username": "account-b",
    "secret_type": "password",
    "secret": "******"
  }
}
```

配置文件权限为 `0600`，只保留当前版本，不生成密码历史或备份文件。

### 托管交付

应用不能直接读取 `credentials.json` 时，可由主机管理员在 `agent.json` 中配置 `deliveries`。Agent 将指定字段写成 POSIX shell 兼容的环境文件，执行本机生效脚本；脚本返回 0 且凭据仍是当前版本后，`confirmation: apply` 会自动确认。脚本必须完成应用重载或重启及健康检查，不能只表示命令已提交：

```json
{
  "deliveries": {
    "cred-pg-main": {
      "format": "env",
      "path": "/etc/jumpserver-pam/deliveries/database.env",
      "fields": {
        "DB_USER": "username",
        "DB_PASSWORD": "secret"
      },
      "owner": "order-service",
      "mode": "0600",
      "apply": ["/usr/local/sbin/apply-order-service"],
      "timeout": 120,
      "confirmation": "apply"
    }
  }
}
```

Agent 仅接受当前凭据中的 `key`、`revision`、`asset_id`、`address`、`account_id`、`username`、`secret_type` 和 `secret` 字段；环境文件不支持 NUL 或换行。交付路径必须位于 root 所有且组/其他用户不可写的目录下，路径中不能包含符号链接。生效脚本必须是 root 所有的绝对路径普通文件，不能是符号链接或允许组/其他用户写入。Agent 使用参数数组执行，不经过 shell，也不把密码放入参数、环境或日志。脚本读取 `JMS_PAM_EVENT`（`published` 或 `revoked`）、`JMS_PAM_CREDENTIAL_KEY`、`JMS_PAM_REVISION` 和 `JMS_PAM_CREDENTIAL_FILE`；撤权时目标环境文件已删除，同一脚本返回非 0 会持续重试。交付状态保存在 `/var/lib/jumpserver-pam/delivery-state.json`，apply 失败、Agent 重启或确认请求失败都不会误确认或重复执行已经成功的 apply。

未配置 `deliveries` 或使用 `confirmation: manual` 时保留原有文件读取与 CLI/HTTP 手工确认流程。交付配置和脚本只在 Agent 主机本地维护，不由 JumpServer 服务端下发任意命令。

### 重新安装与注册失败恢复

- 本机重新安装时，使用与原配置一致的地址、实例标识、文件路径、应用用户和端口。安装器验证并复用现有身份，不提交新注册令牌、不清空确认状态；随后重启服务并检查 `systemctl is-active`。此检查证明服务已启动，不等于业务已完成凭据切换。
- 没有本地配置时，服务端拒绝覆盖同名实例，包括已停用实例。不要通过重复注册重置一个仍在使用的客户端。
- 首次注册超时、响应丢失或身份文件保存失败时，先在后台检查实例是否已创建。优先恢复原本地身份文件；确实无法恢复时，核实旧实例已不再使用，再按正常管理流程清理旧实例，或选择新的实例标识和新令牌重新部署。旧实例仍启用时可能继续阻塞轮换，不要为了重试盲目停用正在承载业务的实例。
- 本地身份验证失败时保留原配置，先检查网络、应用/配置/实例是否停用。重新安装不会自动启用实例或替换密钥。

## 可选事件通知

在客户端接入配置中启用「事件通知」。SDK 注册 Python 回调，Agent 填写应用的 HTTP(S) 通知地址；没有启用通知时继续按原方式定期取密。应用仍需明确确认使用的版本。

SDK 在应用进程启动时注册一次，关闭时停止。监听不依赖首次取密成功，应用可直接把事件转交自己的消息队列或处理函数：

```python
client = JumpServerPAMClient.from_config('jms-pam.json')

def on_event(event):
    # event 只含事件 ID、实例标识、凭据 key、版本等元数据，不含密码。
    application_event_queue.put(event)

listener = client.start_events(handler=on_event)
# 继续运行应用；处理 credential.published 时 get_credential(event['key'])，
# 核对版本，重连成功后 confirm_applied(credential)。
# 关闭应用时：client.close()
```

回调正常返回表示送达，抛异常表示失败。回调应快速返回，不要在回调里长时间等待；超过服务端 60 秒领取期限可能重复处理。`listener.last_error` 可查看连接 JumpServer 的最近错误。停止通知可调用 `client.stop_events()`，取密不受影响。

Agent 使用同一事件监听、领取和结果上报逻辑，在本机向配置的通知地址 POST JSON。仅 HTTP 2xx 表示送达，不跟随重定向，不发送认证头。本版仅面向受信任的同机/同执行环境应用接口，不要把接口暴露到不受信任网络。通知 URL 变更后更新本地配置并重启 Agent，不要重新注册替换身份；配置禁用则停止通知。

Agent 收到 `credential.published` 后先获取并原子写入本地凭据文件，文件版本与事件一致才通知应用；如果该事件版本已经过时，记录失败，不冒充送达。应用读取文件、使用该版本后，通过 CLI 的 `--revision`，或本机 `POST /v1/confirm` 的 `{"key":"cred-pg-main","revision":2}` 确认。只传 key 不再支持，以免确认了应用尚未使用的新版本。

事件代码：`credential.published`（新版本可用）、`credential.unavailable`（单账号改密中）、`rotation.failed`（改密失败）、`access.revoked`（凭据授权撤销）。停用身份或认证被拒绝时，本地监听器发出一次 `access.stopped`，标记 `origin: client`；它不是服务端下发事件，服务端拒绝该身份后也不能继续上报通知结果。

同一服务端事件对每个启用监听的实例单独投递。应用使用 `event_id + client_id` 识别重复事件；`client_id` 是全局唯一实例 ID，`instance_id` 是可读名称，在不同配置间可能重复。服务端最多安排 5 次尝试（失败后等待 5、15、30、60 秒），10 分钟未送达记为失败；离线恢复后可继续未过期任务。SDK/Agent 不另做一层业务重试，结果上报网络失败时先重报结果。**通知送达、取到凭据、确认生效是三个不同动作。** 通知与失败结果显示在应用管理的全局审计日志中。

本版旧调用记录入口/API 停用，历史数据保留；新记录只写统一审计。旧 `account-secret` 取密接口的兼容期不受影响。

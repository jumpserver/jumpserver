# JumpServer PAM Node.js SDK

本 SDK 与 Python 凭据策略 SDK 对齐：获取授权账号或轮换策略凭据、确认生效版本、监听事件、处理应用指令、同步 Agent 状态。请求 URL、HMAC 签名、Digest、UTC 时间、请求 ID 和协议头均由客户端自动生成。

## 环境要求

- Node.js 20.3+ / ws
- `demo.js`

## 配置与运行

安装源码 SDK，填写下方配置。在应用管理中授权可 pull 的账号；只有需要 push 或轮换时才绑定凭据策略。从应用接入材料获取应用 AK/SK 和组织 ID。替换占位符，将身份材料保存在部署密钥中，每个副本使用稳定、唯一的实例 ID。取密只能选择账号 ID 或策略 key 中的一种。

```bash
cd apps/accounts/clients/node
export JMS_ENDPOINT='https://jumpserver.example.com'
export JMS_APP_ID='<app-id>'
export JMS_APP_SECRET='<app-secret>'
export JMS_ORG_ID='<org-id>'
export JMS_INSTANCE_ID='app-node-1'
export JMS_ACCOUNT_ID='<account-id>'

npm ci
node demo.js
```

SDK 当前从本仓库源码安装，尚未发布到公共包仓库。将 /path/to/jumpserver 替换为绝对路径；Go 和 Node.js 安装命令在应用目录执行，Java 依赖添加到应用 pom.xml。仓库运行示例的本地导入在应用中应替换为下方包导入。

```bash
npm install /path/to/jumpserver/apps/accounts/clients/node
```

```javascript
const { Client } = require('@jumpserver/pam')
// ESM: import { Client } from '@jumpserver/pam'
```

## 请求与响应

```javascript
'use strict'

const { Client } = require('./index')

async function main() {
  const client = new Client({
    endpoint: process.env.JMS_ENDPOINT,
    appId: process.env.JMS_APP_ID,
    appSecret: process.env.JMS_APP_SECRET,
    instanceId: process.env.JMS_INSTANCE_ID,
    orgId: process.env.JMS_ORG_ID,
  })
  try {
    const credential = await client.getCredential({ accountId: process.env.JMS_ACCOUNT_ID })
    // Pass credential.account.username / secret to the application connection pool.
    console.log(
      `Fetched revision ${credential.revision}; implement application credential switching.`,
    )
  } finally {
    client.close()
  }
}

if (require.main === module)
  main().catch((error) => {
    console.error(error.code || error.name)
    process.exitCode = 1
  })
```

## 事件处理接口

先在本地初始化账号映射或连接池，再显式启动监听。Python 和 Node.js 使用子类钩子，Go 使用 EventHandlers，Java 使用 CredentialEventListener。示例中的连接切换函数必须由业务实现，否则会抛错。原有迭代器或回调接口继续保留。

```javascript
'use strict'
const { Client } = require('./index')

class MyClient extends Client {
  constructor(options) {
    super(options)
    this.credentials = new Map()
    this.modes = new Map()
  }
  async onEvent(event) {
    if (event.event === 'snapshot') {
      this.modes.clear()
      for (const update of event.credentials || [])
        this.modes.set(update.credentialKey || update.key, update.credentialMode)
      for (const key of this.credentials.keys())
        if (!this.modes.has(key)) this.credentials.delete(key) // Also release connections.
    } else if (event.event === 'credential.updated') {
      this.modes.set(event.credentialKey || event.key, event.credentialMode)
    }
    // Use executeApplicationCommand for command events; see events.js.
  }
  async onCredentialChanged(credential, { signal }) {
    await this.applyCredential(credential, { signal })
    if (this.modes.get(credential.key) === 'alternating_rotation')
      await this.confirmCredential({ key: credential.key, revision: credential.revision,
        accountId: credential.account.id, signal })
    this.credentials.set(credential.key, credential)
  }
  async applyCredential(credential, { signal }) {
    throw new Error('Implement connection validation, pool switching and old connection cleanup')
  }
  async onCredentialRevoked(event) {
    this.credentials.delete(event.credentialKey || event.key) // Also release affected connections.
  }
}

async function main() {
  const client = new MyClient({ endpoint: process.env.JMS_ENDPOINT, appId: process.env.JMS_APP_ID,
    appSecret: process.env.JMS_APP_SECRET, instanceId: process.env.JMS_INSTANCE_ID, orgId: process.env.JMS_ORG_ID })
  const stop = () => client.close()
  process.once('SIGINT', stop); process.once('SIGTERM', stop)
  try { await client.watchEvents() }
  finally {
    client.close(); await client.stopEvents()
    process.removeListener('SIGINT', stop); process.removeListener('SIGTERM', stop)
  }
}
if (require.main === module) main().catch((error) => {
  console.error(error.code || error.name); process.exitCode = 1
})
module.exports = { MyClient }
```

首次与重连 snapshot、credential.updated 按策略模式取密，再串行调用凭据处理函数。读取器与业务处理通过容量为 128 的有界队列连接；队列满时产生背压。取密或凭据处理失败按 1–30 秒指数退避重试，每次重新取密。同一目标的新事件替换待重试项；快照重置重试范围，撤销或配置变更取消待重试项。处理函数应支持重复调用。原始事件和撤销钩子的异常进入错误处理，不自动重试；指令仍需通过认领接口执行。received 仅表示读取事件，SDK 不会自动确认轮换。较旧版本事件不会取消较新版本的拉取重试。

`watchEvents({signal})` / `startEvents({signal})`; `stopEvents()` / `await subscription.stop()` / `await subscription.done`

watchEvents 等待完成且不阻塞事件循环；startEvents 返回不代表初始同步完成。每个客户端允许一个高层监听器。异步钩子逐个 await，并收到 AbortSignal。close 同步请求取消，由外部 await subscription.stop() 或 done 等待结束。钩子可 await stopEvents，但不要等待自己的 done。clone 返回新的基础 Client。

### 最新凭据与后端不可用

取密始终先请求 API。成功获取新凭据后替换本地保留值，更旧版本不会覆盖已获取的新版本；保留值不按时间过期。只有 API 超时、网络故障或 HTTP 5xx 时，才返回相同查询条件下已获取的最新凭据，并设置本地来源标记。首次获取失败且没有保留值时，抛出原始错误。SDK 在当前客户端内存中保留这些值，直到更新、撤销或关闭；clone 和进程重启从空状态开始。Agent 通过已有受保护的本地状态保留最新凭据。HTTP 401/403/404、client_upgrade_required 清空 SDK 的保留值并报错，成功响应格式错误也会报错。明确撤销删除相应凭据，push 快照移除订阅范围外的 push 项；配置变更通知先保留已有值，由后续快照核对授权范围。Agent 在 HTTP 同步前先执行明确撤销或快照授权范围缩小并保存范围，后端故障期间或重启后也会阻止相应本地取密。credential_not_found（HTTP 400）同样清除 SDK 保留值。 按 account_id 直接 pull 始终需要实时 API 响应；push 快照不能证明缓存的 pull 凭据仍获授权。

- `credential.fromLocal`
- `getCredential({key, allowLocalFallback: false})` / `getCredential({accountId, allowLocalFallback: false})`

启用高层事件监听后，snapshot、credential.updated 会自动获取当前凭据并替换本地保留值，再调用业务处理函数。刷新失败时保留上一份凭据并重试。Agent 同样在更新通知后主动取密，后端故障期间保留已有凭据。事件刷新和手动切换使用下方必须实时获取的调用；保留的密码不能被当成刚获取的新版本，也不会自动确认轮换。

事件连接空闲时每 10 秒发送应用层 ping，约 30 秒收不到消息则重连。重连采用 1–30 秒指数退避并重新签名。重连快照恢复当前状态，不重放历史事件。



## 事件与凭据生效

处理首次/重连 snapshot 和 credential.updated。下方完整事件示例分别处理 subscription、alternating_rotation 及应用指令。替换凭据应用函数：验证真实连接、切换连接池并释放旧连接。占位函数会抛出异常，防止确认尚未应用的版本；应用本地状态还须按快照移除已撤销账号，并处理撤销事件。

```javascript
'use strict'
const { Client } = require('./index')

async function applyCredential(credential) {
  // Validate a real connection, switch the pool, then release old connections.
  throw new Error('Implement application credential switching')
}
async function restartApplication() {
  throw new Error('Implement application restart and health check')
}
async function handleCommand(client, event) {
  if (event.event === 'application.restart.requested') return restartApplication()
  if (event.event !== 'credential.switch.requested')
    throw new Error('Unsupported application command')
  const credential = await client.getCredential({ key: event.credentialKey, allowLocalFallback: false })
  if (credential.revision !== event.revision || credential.account.id !== event.accountId)
    throw new Error('Requested account version is superseded')
  await applyCredential(credential)
  await client.confirmCredential({
    key: credential.key,
    revision: credential.revision,
    accountId: credential.account.id,
  })
}
async function main() {
  const client = new Client({
    endpoint: process.env.JMS_ENDPOINT,
    appId: process.env.JMS_APP_ID,
    appSecret: process.env.JMS_APP_SECRET,
    instanceId: process.env.JMS_INSTANCE_ID,
    orgId: process.env.JMS_ORG_ID,
  })
  const stop = () => client.close()
  process.once('SIGINT', stop)
  process.once('SIGTERM', stop)
  try {
    for await (const event of client.watchCredentialEvents()) {
      if (event.commandId) {
        try {
          await client.executeApplicationCommand(event, (command) => handleCommand(client, command))
        } catch {
          /* Failure is reported; keep secrets out of logs. */
        }
        continue
      }
      const updates =
        event.event === 'snapshot'
          ? event.credentials
          : event.event === 'credential.updated'
            ? [event]
            : []
      // On snapshots, remove application caches absent from the new authorized scope.
      for (const update of updates || []) {
        const mode = update.credentialMode
        const key = update.credentialKey || update.key
        let credential
        if (mode === 'subscription' && update.accountId && key) {
          const subscriptionKey = key.endsWith(`:${update.accountId}`) ? key : `${key}:${update.accountId}`
          credential = await client.getCredential({ key: subscriptionKey, allowLocalFallback: false })
        }
        else if (mode === 'alternating_rotation' && key)
          credential = await client.getCredential({ key, allowLocalFallback: false })
        else continue
        await applyCredential(credential)
        if (mode === 'alternating_rotation')
          await client.confirmCredential({
            key: credential.key,
            revision: credential.revision,
            accountId: credential.account.id,
          })
      }
    }
  } finally {
    client.close()
    process.removeListener('SIGINT', stop)
    process.removeListener('SIGTERM', stop)
  }
}
if (require.main === module)
  main().catch((error) => {
    console.error(error.code || error.name)
    process.exitCode = 1
  })
```

交替轮换需要先验证真实连接、切换应用连接池并释放旧连接，再确认准确的 key、revision 和 account_id。凭据变更订阅无需确认，连接验证失败时不得确认。

## 应用指令

轮询、指令认领和结果上报均通过 SDK 方法完成，只有认领成功才执行处理函数。切换指令校验请求的版本与账号、应用凭据后再确认；重启指令须完成重启及健康检查。工作完成后才报告成功，失败上报不会掩盖原始业务异常。

## 常用方法

- `getCredential({key})`
- `getCredential({accountId})`
- `getCredential({key, allowLocalFallback: false})`
- `confirmCredential({key, revision, accountId})`
- `watchCredentialEvents({signal})`
- `watchEvents({signal}) / startEvents({signal}) / stopEvents()`
- `EventSubscription.stop() / done`
- `listApplicationCommands()`
- `reportApplicationCommandResult({commandId, status, errorCode})`
- `executeApplicationCommand(event, handler)`
- `syncAgent({credentials, deliveredCredentials, ...})`
- `clone() / close()`

## 排查问题

HTTP、网络、认证和响应解码错误使用 SDK 异常或错误类型，包含错误码及 HTTP 状态。使用完成后关闭事件流与客户端，克隆客户端具有独立生命周期。在业务边界重试临时故障，不记录密码或认证请求头。

`PAMError`

各 SDK 使用版本 1 协议，Agent 配置格式为版本 1。收到 client_upgrade_required（HTTP 426）时检查兼容性并升级。允许未知可选字段及通知事件，未实现的策略类型不得应用或确认。事件接收回执由 SDK 自动发送，不能作为凭据已经生效的证明。

## Go Agent 接入

身份只需要 app_id、app_secret、org_id 和稳定的 instance_id；应用授权控制 pull 范围，绑定策略控制 push 范围。文件路径和服务动作全部在本机配置：state_file 始终保留最新密码，event_file 追加不含密码的事件元数据，delivery 定义默认交付，rules 定义文件、模板及 reload/restart 或固定脚本。收到更新通知后主动取最新密码，先持久化，再原子替换文件，最后执行动作；交付失败会重试。规则使用 get_accounts 返回的 credentials[].key，订阅 push 的 key 为 account:<account-id>，不包含策略 key。rules 为空时默认按 key 写文件。

本机 rules 配置目标文件、JSON/EnvironmentFile 或可信模板，以及可选的 systemd reload/restart 或固定可执行脚本。脚本通过标准输入接收凭据 JSON，参数固定、有超时，并应在验证业务生效后返回成功。Core 不能新增脚本路径或扩大本机能力。修改私有配置后重启 Agent。

下载的引导配置已包含 Agent 身份和交付设置。只需在 rules 中声明业务使用的账号 ID，再配置更新业务文件、生效动作和运行中连接验证。账号设置 allow_account_switch 后可沿用同一规则处理 A/B 双向轮换；可选 credential_check 用于改文件前验证新账号。状态、事件、Socket 路径和 300 秒对账周期均有默认值。rules 为空时按凭据写默认文件。

```json
{
  "endpoint": "https://jumpserver.example.com",
  "app_id": "<application-id>",
  "app_secret": "<application-secret>",
  "org_id": "<org-id>",
  "instance_id": "orders-node-1",
  "delivery": {
    "delivery_mode": "json",
    "delivery_root": "/opt/jumpserver-pam/credentials",
    "app_user": "orders"
  },
  "rules": []
}
```

`rules`:

```json
[
  {
    "accounts": [
      {
        "account_id": "<primary-account-id>",
        "allow_account_switch": true
      }
    ],
    "config_update": {
      "file": "/etc/order-service/config.yml",
      "fields_map": {
        "DB_USER": "username",
        "DB_PASSWORD": "secret"
      }
    },
    "service_action": {
      "unit": "order-service.service",
      "operation": "restart"
    },
    "application_check": {
      "path": "/usr/local/libexec/jms-pam/check-running-db",
      "confirm_on_success": true
    }
  }
]
```

```bash
jms-pam-agent get_accounts
jms-pam-agent get_secret '<account-id>'
sudo jms-pam-agent check-config
sudo systemctl restart jms-pam-agent
```

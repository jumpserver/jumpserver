# JumpServer PAM Node.js SDK

本 SDK 与 Python 凭据策略 SDK 对齐：获取授权账号或轮换策略凭据、确认生效版本、监听事件、处理应用指令、同步 Agent 状态。请求 URL、HMAC 签名、Digest、UTC 时间、请求 ID 和协议头均由客户端自动生成。

## 环境要求

- Node.js 20.3+ / ws
- `demo.js`

## 配置与运行

安装源码 SDK，填写下方配置。在应用管理中授权账号并绑定策略，从应用接入材料获取应用 AK/SK 和组织 ID。替换占位符，将身份材料保存在部署密钥中，每个副本使用稳定、唯一的实例 ID。取密只能选择账号 ID 或策略 key 中的一种。

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

## 事件与凭据生效

处理首次/重连 snapshot 和 credential.updated。下方完整事件示例分别处理 subscription、alternating_rotation 及应用指令。替换凭据应用函数：验证真实连接、切换连接池并释放旧连接。占位函数会抛出异常，防止确认尚未应用的版本；应用缓存还须按快照移除已撤销账号，并处理撤销事件。

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
  const credential = await client.getCredential({ key: event.credentialKey })
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
        if (mode === 'subscription' && update.accountId)
          credential = await client.getCredential({ accountId: update.accountId })
        else if (mode === 'alternating_rotation' && key)
          credential = await client.getCredential({ key })
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
- `confirmCredential({key, revision, accountId})`
- `watchCredentialEvents({signal})`
- `listApplicationCommands()`
- `reportApplicationCommandResult({commandId, status, errorCode})`
- `executeApplicationCommand(event, handler)`
- `syncAgent({credentials, deliveredCredentials, ...})`
- `clone() / close()`

## 排查问题

HTTP、网络、认证和响应解码错误使用 SDK 异常或错误类型，包含错误码及 HTTP 状态。使用完成后关闭事件流与客户端，克隆客户端具有独立生命周期。在业务边界重试临时故障，不记录密码或认证请求头。

`PAMError`

各 SDK 使用版本 1 协议，Agent 配置格式为版本 1。收到 client_upgrade_required（HTTP 426）时检查兼容性并升级。允许未知可选字段及通知事件，未实现的策略类型不得应用或确认。事件接收回执由 SDK 自动发送，不能作为凭据已经生效的证明。

## Linux Agent 接入

Agent 同步方法供 Agent 实现复用，需要 Agent 身份或 source 及配置 ID，使用 KnownRevision 上报缓存与交付版本。目前 Linux 安装、文件交付和本地 API 由 Python Agent 提供，各编程语言的应用均可接入该 Agent。

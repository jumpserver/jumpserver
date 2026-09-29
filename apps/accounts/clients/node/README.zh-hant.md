# JumpServer PAM Node.js SDK

本 SDK 與 Python 憑證策略 SDK 對齊：取得授權帳號或輪換策略憑證、確認生效版本、監聽事件、處理應用程式指令及同步 Agent 狀態。請求 URL、HMAC 簽章、Digest、UTC 時間、請求 ID 與協定標頭均由客戶端自動產生。

## 環境需求

- Node.js 20.3+ / ws
- `demo.js`

## 設定與執行

安裝原始碼 SDK 並填寫下方設定。在應用程式管理中授權帳號及綁定策略，從接入資料取得應用程式 AK/SK 與組織 ID。替換預留值並保護身分資料，每個副本使用穩定且唯一的實例 ID。取密只能選擇帳號 ID 或策略 key 中的一種。

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

SDK 目前從本儲存庫原始碼安裝，尚未發佈至公開套件庫。將 /path/to/jumpserver 替換為絕對路徑；Go 和 Node.js 安裝命令在應用程式目錄執行，Java 相依套件加入應用程式 pom.xml。儲存庫範例的本地匯入應替換為下方套件匯入。

```bash
npm install /path/to/jumpserver/apps/accounts/clients/node
```

```javascript
const { Client } = require('@jumpserver/pam')
// ESM: import { Client } from '@jumpserver/pam'
```

## 請求與回應

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

## 事件與憑證生效

處理首次/重新連線 snapshot 與 credential.updated。下方完整範例分別處理 subscription、alternating_rotation 及應用程式指令。實作憑證套用函式：驗證真實連線、切換連線池及釋放舊連線。預留函式會拋出例外，避免確認尚未套用的版本；快取也須依快照移除已撤銷帳號並處理撤銷事件。

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

交替輪換需先驗證真實連線、切換應用程式連線池並釋放舊連線，再確認準確的 key、revision 和 account_id。憑證變更訂閱無需確認，連線驗證失敗時不得確認。

## 應用程式指令

輪詢、指令認領及結果回報均透過 SDK 方法完成，只有認領成功才執行處理函式。切換指令須驗證版本與帳號，套用後再確認；重新啟動指令須完成重啟及健康檢查。完成後才回報成功，失敗回報保留原始業務例外。

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

## 問題排查

HTTP、網路、認證及解碼錯誤使用 SDK 例外或錯誤類型，包含錯誤碼與 HTTP 狀態。使用完畢後關閉事件流與客戶端，複製客戶端具有獨立生命週期。在業務邊界重試暫時故障，不記錄密碼或認證標頭。

`PAMError`

各 SDK 使用版本 1 協定，Agent 設定格式為版本 1。收到 client_upgrade_required（HTTP 426）時檢查相容性並升級。允許未知可選欄位及通知事件，未實作的策略類型不得套用或確認。SDK 自動傳送接收回執，不能作為憑證已生效的證明。

## Linux Agent 接入

Agent 同步方法供 Agent 實作共用，需要 Agent 身分或 source 與設定 ID，以 KnownRevision 回報快取及交付版本。目前 Linux 安裝、檔案交付與本地 API 由 Python Agent 提供，各程式語言的應用程式均可使用。

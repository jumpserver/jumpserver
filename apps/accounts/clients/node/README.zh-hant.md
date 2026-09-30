# JumpServer PAM Node.js SDK

本 SDK 與 Python 憑證策略 SDK 對齊：取得授權帳號或輪換策略憑證、確認生效版本、監聽事件、處理應用程式指令及同步 Agent 狀態。請求 URL、HMAC 簽章、Digest、UTC 時間、請求 ID 與協定標頭均由客戶端自動產生。

## 環境需求

- Node.js 20.3+ / ws
- `demo.js`

## 設定與執行

安裝原始碼 SDK 並填寫下方設定。在應用程式管理中授權可 pull 的帳號；僅在需要 push 或輪換時綁定憑據策略。從接入資料取得應用程式 AK/SK 與組織 ID。替換預留值並保護身分資料，每個副本使用穩定且唯一的實例 ID。取密只能選擇帳號 ID 或策略 key 中的一種。

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

## 事件處理介面

先初始化本地帳號映射或連線池，再啟動監聽。Python 和 Node.js 使用子類別鉤子，Go 使用 EventHandlers，Java 使用 CredentialEventListener。必須實作範例中的連線切換函式；原有迭代器與回呼介面繼續保留。

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

首次與重連 snapshot、credential.updated 按策略模式取密，再循序呼叫憑據處理函式。讀取器和業務處理使用容量 128 的有界佇列；滿載時產生背壓。取密或處理失敗按 1–30 秒指數退避重試，每次重新取密。新事件替換同一目標的重試；快照重設範圍，撤銷與設定變更取消重試。處理須可重複執行。原始事件與撤銷鉤子不自動重試；指令仍須認領。received 僅表示已讀取，SDK 不自動確認輪換。較舊版本事件不會取消較新版本的取密重試。

`watchEvents({signal})` / `startEvents({signal})`; `stopEvents()` / `await subscription.stop()` / `await subscription.done`

watchEvents 不阻塞事件迴圈；startEvents 不代表同步完成。每個客戶端只有一個高層監聽器。非同步鉤子循序 await 並收到 AbortSignal。close 取消後，由外部等待 stop() 或 done。鉤子勿等待自己的 done。clone 返回基礎 Client。

### 最新憑據與後端不可用

取密先請求 API。成功取得新憑據後替換本地保留值，舊版本不覆蓋新版本，且不按時間過期。僅在逾時、網路故障或 HTTP 5xx 時，返回相同查詢條件下已取得的最新憑據並標記本地來源；沒有保留值則拋出原始錯誤。SDK 在目前客戶端記憶體內保留，直到更新、撤銷或關閉；clone 與重新啟動不繼承。Agent 使用既有受保護的本地狀態保存。HTTP 401/403/404 或 client_upgrade_required 清空 SDK 保留值並報錯，成功回應格式錯誤也報錯。明確撤銷移除對應憑據；快照移除授權範圍外項目；設定變更先保留，由後續快照核對範圍。Agent 在 HTTP 同步前先執行明確撤銷或快照授權範圍縮小並保存範圍，後端故障期間或重新啟動後也會阻止相應本地取密。credential_not_found（HTTP 400）同樣清除 SDK 保留值。 以 account_id 直接 pull 一律需要即時 API 回應；push 快照不能證明快取的 pull 憑據仍獲授權。

- `credential.fromLocal`
- `getCredential({key, allowLocalFallback: false})` / `getCredential({accountId, allowLocalFallback: false})`

啟用高層監聽後，snapshot、credential.updated 自動取密、替換保留值，再呼叫業務函式。刷新失敗保留上一份並重試。Agent 也在更新通知後主動取密，後端故障時保留已有值。刷新與手動切換使用下方即時取得的呼叫；本地保留值不代表剛取得新版本，亦不自動確認輪換。

閒置時每 10 秒傳送應用層 ping，約 30 秒收不到訊息則重連，以 1–30 秒指數退避並重新簽章。快照恢復目前狀態，不重播歷史事件。



## 事件與憑證生效

處理首次/重新連線 snapshot 與 credential.updated。下方完整範例分別處理 subscription、alternating_rotation 及應用程式指令。實作憑證套用函式：驗證真實連線、切換連線池及釋放舊連線。預留函式會拋出例外，避免確認尚未套用的版本；應用程式本地狀態也須依快照移除已撤銷帳號並處理撤銷事件。

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

交替輪換需先驗證真實連線、切換應用程式連線池並釋放舊連線，再確認準確的 key、revision 和 account_id。憑證變更訂閱無需確認，連線驗證失敗時不得確認。

## 應用程式指令

輪詢、指令認領及結果回報均透過 SDK 方法完成，只有認領成功才執行處理函式。切換指令須驗證版本與帳號，套用後再確認；重新啟動指令須完成重啟及健康檢查。完成後才回報成功，失敗回報保留原始業務例外。

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

## 問題排查

HTTP、網路、認證及解碼錯誤使用 SDK 例外或錯誤類型，包含錯誤碼與 HTTP 狀態。使用完畢後關閉事件流與客戶端，複製客戶端具有獨立生命週期。在業務邊界重試暫時故障，不記錄密碼或認證標頭。

`PAMError`

各 SDK 使用版本 1 協定，Agent 設定格式為版本 1。收到 client_upgrade_required（HTTP 426）時檢查相容性並升級。允許未知可選欄位及通知事件，未實作的策略類型不得套用或確認。SDK 自動傳送接收回執，不能作為憑證已生效的證明。

## Go Agent 接入

身分只需要 app_id、app_secret、org_id 和穩定的 instance_id；授權範圍跟隨應用程式綁定的策略。檔案路徑及服務動作全部在本機設定：state_file 保留最新密碼，event_file 追加不含密碼的事件資料，delivery 定義預設交付，rules 定義檔案、範本及 reload/restart 或固定腳本。收到更新通知後取得最新密碼，先持久化，再原子替換檔案，最後執行動作；交付失敗會重試。規則使用 get_accounts 回傳的 credentials[].key，訂閱 key 包含帳號 ID。rules 為空時預設依 key 寫檔。

本機 rules 設定目標檔案、JSON/EnvironmentFile 或可信範本，以及可選的 systemd reload/restart 或固定可執行腳本。腳本透過標準輸入接收憑據 JSON，參數固定、有逾時，並應在驗證業務生效後回報成功。Core 不能新增腳本路徑或擴大本機能力。修改私有設定後重新啟動 Agent。

身分只需要 app_id、app_secret、org_id 和穩定的 instance_id；授權範圍跟隨應用程式綁定的策略。檔案路徑及服務動作全部在本機設定：state_file 保留最新密碼，event_file 追加不含密碼的事件資料，delivery 定義預設交付，rules 定義檔案、範本及 reload/restart 或固定腳本。收到更新通知後取得最新密碼，先持久化，再原子替換檔案，最後執行動作；交付失敗會重試。規則使用 get_accounts 回傳的 credentials[].key，訂閱 key 包含帳號 ID。rules 為空時預設依 key 寫檔。

```json
{
  "endpoint": "https://jumpserver.example.com",
  "app_id": "<application-id>",
  "app_secret": "<application-secret>",
  "org_id": "<org-id>",
  "instance_id": "orders-node-1",
  "state_file": "/var/lib/jms-pam-agent/state.json",
  "event_file": "/var/lib/jms-pam-agent/events.jsonl",
  "reconcile_interval": 300,
  "delivery": {
    "delivery_mode": "json",
    "delivery_root": "/opt/jumpserver-pam/credentials",
    "socket_path": "/run/jms-pam-agent/agent.sock",
    "app_user": "orders",
    "systemd_unit": "",
    "systemd_action": ""
  },
  "rules": []
}
```

`rules`:

```json
[
  {
    "keys": [
      "<credential-key>"
    ],
    "files": [
      {
        "path": "/etc/order-service/database.json",
        "format": "template",
        "template_file": "/etc/jms-pam-agent/orders-db.tmpl",
        "owner": "orders"
      }
    ],
    "action": {
      "type": "systemd",
      "unit": "order-service.service",
      "operation": "reload",
      "timeout_seconds": 30
    }
  }
]
```

`/etc/jms-pam-agent/orders-db.tmpl`:

```gotemplate
{
  "username": {{json (index .Credentials "<credential-key>").Username}},
  "password": {{json (index .Credentials "<credential-key>").Secret}}
}
```

```bash
jms-pam-agent get_accounts
jms-pam-agent get_secret '<account-id>'
sudo jms-pam-agent check-config
sudo systemctl restart jms-pam-agent
```

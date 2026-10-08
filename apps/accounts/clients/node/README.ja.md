# JumpServer PAM Node.js SDK

本 SDK は Python の認証情報ポリシー SDK と同じ機能を提供します。許可されたアカウントやローテーションポリシーの認証情報取得、適用済み版の確認、イベント購読、アプリケーションコマンド処理、Agent 同期を行います。URL、HMAC 署名、Digest、UTC 日時、リクエスト ID、プロトコルヘッダーは自動生成されます。

## 動作要件

- Node.js 20.3+ / ws
- `demo.js`

## 設定と実行

ソース SDK をインストールし、下記を設定します。アプリケーション管理で pull 対象のアカウントを許可し、push またはローテーションが必要な場合だけポリシーを関連付けます。接続資料から AK/SK と組織 ID を取得してください。プレースホルダーを置き換え、認証資料を安全に保管します。各レプリカには安定した一意のインスタンス ID を使い、取得にはアカウント ID またはポリシー key の一方だけを指定します。

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

SDK は現在このリポジトリのソースからインストールし、公開パッケージレジストリには未公開です。/path/to/jumpserver を絶対パスに置き換えます。Go と Node.js のインストールはアプリケーションのディレクトリで実行し、Java の依存関係は pom.xml に追加します。リポジトリの実行例のローカルインポートは以下のパッケージインポートに置き換えてください。

```bash
npm install /path/to/jumpserver/apps/accounts/clients/node
```

```javascript
const { Client } = require('@jumpserver/pam')
// ESM: import { Client } from '@jumpserver/pam'
```

## リクエストとレスポンス

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

## イベントハンドラー

ローカル状態を初期化してから監視を開始します。Python と Node.js はサブクラス、Go は EventHandlers、Java は CredentialEventListener を使用します。例の接続切替処理を実装してください。従来の API も利用できます。

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

初回・再接続の snapshot と credential.updated はモード別に認証情報を取得し、ハンドラーを順番に呼び出します。受信と処理は上限 128 件のキューで接続され、満杯時は受信を待機します。取得・適用の失敗は 1–30 秒の指数バックオフで再試行し、毎回取得し直します。同じ対象の更新は再試行を置換し、snapshot は範囲を更新、失効・設定変更は再試行を解除します。処理は繰り返し可能にしてください。観測・失効フックは自動再試行しません。コマンドは実行権の取得が必要です。received は受信のみを示し、SDK はローテーションを自動確認しません。古いリビジョンのイベントは、新しいリビジョンの取得の再試行を取り消しません。

`watchEvents({signal})` / `startEvents({signal})`; `stopEvents()` / `await subscription.stop()` / `await subscription.done`

watchEvents はイベントループをブロックしません。startEvents は同期完了を保証しません。監視は 1 つです。async フックは順次 await され AbortSignal を受け取ります。close 後、外部から stop() または done を待ってください。自身の done は待たないでください。clone は基底 Client を返します。

### 最新の認証情報とバックエンド障害

取得はまず API を呼びます。取得成功時に保持値を更新し、古いバージョンで新しい値を上書きせず、時間による有効期限も設けません。タイムアウト、ネットワーク障害、HTTP 5xx の場合だけ、同じ検索条件の最後に取得した値をローカル由来のフラグ付きで返します。保持値がなければ元のエラーです。SDK は更新・失効・終了までクライアントのメモリに保持し、clone や再起動は空から始まります。Agent は保護された既存のローカル状態に保存します。HTTP 401/403/404 または client_upgrade_required は SDK の保持値を消去して失敗し、不正な成功応答も失敗します。失効は対象を、snapshot は認可範囲外を削除します。設定変更時は次の snapshot で範囲を確認するまで保持します。Agent は HTTP 同期の前に明示的な取り消しと snapshot の範囲縮小を適用して保存し、バックエンド障害中や再起動後も該当するローカル取得を停止します。credential_not_found（HTTP 400）でも SDK の保持値を削除します。 account_id による直接 pull には常にライブ API 応答が必要です。push の snapshot はキャッシュされた pull 認可を示しません。

- `credential.fromLocal`
- `getCredential({key, allowLocalFallback: false})` / `getCredential({accountId, allowLocalFallback: false})`

管理された監視を有効にすると、snapshot と credential.updated が自動で取得し、保持値を更新してから業務フックを呼びます。更新失敗時は前の値を保持し再試行します。Agent も更新通知で取得し、障害時は既存値を保持します。更新や手動切替には下記の API 取得必須の呼び出しを使用してください。保持値を新しく取得したバージョンと見なしたり、ローテーションを自動確認したりしません。

アイドル時は 10 秒ごとに ping を送り、約 30 秒メッセージがなければ再接続します。待機は 1–30 秒の指数バックオフで毎回再署名します。snapshot は現在の状態を復元し、履歴イベントは再送しません。



## イベントと認証情報の適用

初回・再接続 snapshot と credential.updated を処理します。下記の完全な例は subscription、alternating_rotation、アプリケーションコマンドを扱います。実接続の検証、接続プールの切替、旧接続の解放を適用関数に実装してください。未実装関数は例外を投げ、未適用版の確認を防ぎます。快照から削除されたアカウントや取り消しイベントをアプリケーションの状態にも反映します。

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

交互ローテーションでは実際の接続を検証し、接続プールを切り替えて古い接続を解放した後に、正確な key、revision、account_id を確認します。認証情報変更の購読では確認は不要です。接続検証に失敗した場合は確認してはいけません。

## アプリケーションコマンド

ポーリング、実行権の取得、結果報告は SDK のメソッドで行います。承認された実行権でのみハンドラーを実行します。切替では要求された版とアカウントを検証し、適用後に確認します。再起動では再起動と正常性確認を行い、完了後に成功を報告します。失敗報告のエラーは元の業務例外を置き換えません。

## 主なメソッド

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

## トラブルシューティング

HTTP、ネットワーク、認証、デコードの失敗はエラーコードと HTTP 状態を含む SDK の例外・エラー型で通知されます。使用後はストリームとクライアントを閉じてください。複製クライアントのライフサイクルは独立しています。一時障害はアプリケーション側で再試行し、秘密情報や認証ヘッダーをログに記録しないでください。

`PAMError`

全 SDK はプロトコル版 1、Agent 設定はスキーマ版 1 を使用します。client_upgrade_required（HTTP 426）を受けたら互換性を確認し更新してください。未知の任意フィールドや通知イベントは許容しますが、未対応ポリシーは適用・確認できません。受領通知は自動送信され、認証情報の適用を証明しません。

## Go Agent の接続

認証には app_id、app_secret、org_id と安定した instance_id を使用し、認可範囲はアプリケーションに関連付けたポリシーに従います。すべてのパスとサービス操作はローカル設定です。state_file は最新パスワードを保持し、event_file は秘密を含まないイベント情報を追記します。delivery は既定の出力、rules はファイル、テンプレートと reload/restart または固定スクリプトを指定します。更新通知で最新値を取得・保存し、ファイルを原子的に置き換えてから操作を実行します。失敗は再試行します。rules の key には get_accounts の credentials[].key を使用します。購読 key にはアカウント ID が含まれます。空の rules は key ごとの既定ファイルを出力します。

ローカル rules でファイル、JSON/EnvironmentFile または信頼済みテンプレートと、systemd reload/restart や固定実行ファイルを設定します。スクリプトは標準入力で認証情報 JSON を受け取り、固定引数とタイムアウトを使い、適用を検証してから成功を返します。Core は実行パスや権限を拡張できません。設定変更後に Agent を再起動します。

ダウンロードした設定には Agent の識別情報と配信設定が含まれます。rules には業務で使うアカウント ID、設定更新、反映操作、稼働中の接続確認を指定します。allow_account_switch を設定したアカウントは A/B の双方向ローテーションに同じルールを使えます。任意の credential_check でファイル更新前に新しいログインを検証できます。状態、イベント、Socket のパスと 300 秒の照合間隔には既定値があります。rules が空なら資格情報ごとに既定ファイルを出力します。

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

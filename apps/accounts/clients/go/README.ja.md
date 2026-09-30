# JumpServer PAM Go SDK

本 SDK は Python の認証情報ポリシー SDK と同じ機能を提供します。許可されたアカウントやローテーションポリシーの認証情報取得、適用済み版の確認、イベント購読、アプリケーションコマンド処理、Agent 同期を行います。URL、HMAC 署名、Digest、UTC 日時、リクエスト ID、プロトコルヘッダーは自動生成されます。

## 動作要件

- Go 1.23+ / coder/websocket
- `cmd/demo/main.go`

## 設定と実行

ソース SDK をインストールし、下記を設定します。アプリケーション管理で pull 対象のアカウントを許可し、push またはローテーションが必要な場合だけポリシーを関連付けます。接続資料から AK/SK と組織 ID を取得してください。プレースホルダーを置き換え、認証資料を安全に保管します。各レプリカには安定した一意のインスタンス ID を使い、取得にはアカウント ID またはポリシー key の一方だけを指定します。

```bash
cd apps/accounts/clients/go
export JMS_ENDPOINT='https://jumpserver.example.com'
export JMS_APP_ID='<app-id>'
export JMS_APP_SECRET='<app-secret>'
export JMS_ORG_ID='<org-id>'
export JMS_INSTANCE_ID='app-node-1'
export JMS_ACCOUNT_ID='<account-id>'

go mod download
go run ./cmd/demo
```

SDK は現在このリポジトリのソースからインストールし、公開パッケージレジストリには未公開です。/path/to/jumpserver を絶対パスに置き換えます。Go と Node.js のインストールはアプリケーションのディレクトリで実行し、Java の依存関係は pom.xml に追加します。リポジトリの実行例のローカルインポートは以下のパッケージインポートに置き換えてください。

```bash
go mod edit -replace=github.com/jumpserver/jumpserver/apps/accounts/clients/go=/path/to/jumpserver/apps/accounts/clients/go
go get github.com/jumpserver/jumpserver/apps/accounts/clients/go@v0.0.0
```

```go
import pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
```

## リクエストとレスポンス

```go
package main

import (
	"context"
	"fmt"
	"log"
	"os"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

func main() {
	client, err := pam.NewClient(pam.Options{
		Endpoint:   os.Getenv("JMS_ENDPOINT"),
		AppID:      os.Getenv("JMS_APP_ID"),
		AppSecret:  os.Getenv("JMS_APP_SECRET"),
		InstanceID: os.Getenv("JMS_INSTANCE_ID"),
		OrgID:      os.Getenv("JMS_ORG_ID"),
	})
	if err != nil {
		log.Fatal("Invalid SDK configuration")
	}
	defer client.Close()
	credential, err := client.GetCredential(context.Background(), pam.CredentialSelector{AccountID: os.Getenv("JMS_ACCOUNT_ID")})
	if err != nil {
		log.Fatalf("Credential fetch failed: %T", err)
	}
	// Pass credential.Account.Username / Secret to the application connection pool.
	fmt.Printf("Fetched revision %d; implement application credential switching.\n", credential.Revision)
}
```

## イベントハンドラー

ローカル状態を初期化してから監視を開始します。Python と Node.js はサブクラス、Go は EventHandlers、Java は CredentialEventListener を使用します。例の接続切替処理を実装してください。従来の API も利用できます。

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

type application struct {
	client      *pam.Client
	credentials map[string]pam.Credential
	modes       map[string]string
}

func (a *application) observe(ctx context.Context, event pam.Event) error {
	updates := []pam.Event{event}
	if event.Event == "snapshot" {
		clear(a.modes)
		updates = event.Credentials
	}
	for _, update := range updates {
		key := update.CredentialKey
		if key == "" {
			key = update.Key
		}
		if key != "" && (event.Event == "snapshot" || event.Event == "credential.updated") {
			a.modes[key] = update.CredentialMode
		}
	}
	if event.Event == "snapshot" {
		for key := range a.credentials {
			if _, ok := a.modes[key]; !ok {
				delete(a.credentials, key) /* Also release connections. */
			}
		}
	}
	// Use ExecuteApplicationCommand for command events; see cmd/events/main.go.
	return nil
}
func applyCredential(ctx context.Context, credential pam.Credential) error {
	return fmt.Errorf("implement connection validation, pool switching and old connection cleanup")
}
func (a *application) changed(ctx context.Context, credential pam.Credential) error {
	if err := applyCredential(ctx, credential); err != nil {
		return err
	}
	if a.modes[credential.Key] == "alternating_rotation" {
		if _, err := a.client.ConfirmCredential(ctx, credential.Key, credential.Revision, credential.Account.ID); err != nil {
			return err
		}
	}
	a.credentials[credential.Key] = credential
	return nil
}
func (a *application) revoked(ctx context.Context, event pam.Event) error {
	delete(a.credentials, event.CredentialKey) // Also release affected connections.
	return nil
}
func main() {
	client, err := pam.NewClient(pam.Options{Endpoint: os.Getenv("JMS_ENDPOINT"), AppID: os.Getenv("JMS_APP_ID"), AppSecret: os.Getenv("JMS_APP_SECRET"), InstanceID: os.Getenv("JMS_INSTANCE_ID"), OrgID: os.Getenv("JMS_ORG_ID")})
	if err != nil {
		log.Fatal("Invalid SDK configuration")
	}
	defer client.Close()
	app := &application{client: client, credentials: make(map[string]pam.Credential), modes: make(map[string]string)}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	err = client.WatchEvents(ctx, pam.EventHandlers{OnEvent: app.observe, OnCredentialChanged: app.changed, OnCredentialRevoked: app.revoked})
	if err != nil && !errors.Is(err, context.Canceled) {
		log.Printf("Event processing failed: %T", err)
	}
}
```

初回・再接続の snapshot と credential.updated はモード別に認証情報を取得し、ハンドラーを順番に呼び出します。受信と処理は上限 128 件のキューで接続され、満杯時は受信を待機します。取得・適用の失敗は 1–30 秒の指数バックオフで再試行し、毎回取得し直します。同じ対象の更新は再試行を置換し、snapshot は範囲を更新、失効・設定変更は再試行を解除します。処理は繰り返し可能にしてください。観測・失効フックは自動再試行しません。コマンドは実行権の取得が必要です。received は受信のみを示し、SDK はローテーションを自動確認しません。古いリビジョンのイベントは、新しいリビジョンの取得の再試行を取り消しません。

`WatchEvents(ctx, handlers)` / `StartEvents(ctx, handlers)`; `Stop()` / `Wait()`; `context.CancelFunc`

WatchEvents は呼出元の goroutine で待ちます。StartEvents は初回同期完了を保証しません。監視は 1 つです。Stop と Close で取消し、ハンドラー外で Wait してください。長い処理は context の取消しに対応してください。

### 最新の認証情報とバックエンド障害

取得はまず API を呼びます。取得成功時に保持値を更新し、古いバージョンで新しい値を上書きせず、時間による有効期限も設けません。タイムアウト、ネットワーク障害、HTTP 5xx の場合だけ、同じ検索条件の最後に取得した値をローカル由来のフラグ付きで返します。保持値がなければ元のエラーです。SDK は更新・失効・終了までクライアントのメモリに保持し、clone や再起動は空から始まります。Agent は保護された既存のローカル状態に保存します。HTTP 401/403/404 または client_upgrade_required は SDK の保持値を消去して失敗し、不正な成功応答も失敗します。失効は対象を、snapshot は認可範囲外を削除します。設定変更時は次の snapshot で範囲を確認するまで保持します。Agent は HTTP 同期の前に明示的な取り消しと snapshot の範囲縮小を適用して保存し、バックエンド障害中や再起動後も該当するローカル取得を停止します。credential_not_found（HTTP 400）でも SDK の保持値を削除します。 account_id による直接 pull には常にライブ API 応答が必要です。push の snapshot はキャッシュされた pull 認可を示しません。

- `credential.FromLocal`
- `GetCredentialFresh(ctx, selector)`

管理された監視を有効にすると、snapshot と credential.updated が自動で取得し、保持値を更新してから業務フックを呼びます。更新失敗時は前の値を保持し再試行します。Agent も更新通知で取得し、障害時は既存値を保持します。更新や手動切替には下記の API 取得必須の呼び出しを使用してください。保持値を新しく取得したバージョンと見なしたり、ローテーションを自動確認したりしません。

アイドル時は 10 秒ごとに ping を送り、約 30 秒メッセージがなければ再接続します。待機は 1–30 秒の指数バックオフで毎回再署名します。snapshot は現在の状態を復元し、履歴イベントは再送しません。



## イベントと認証情報の適用

初回・再接続 snapshot と credential.updated を処理します。下記の完全な例は subscription、alternating_rotation、アプリケーションコマンドを扱います。実接続の検証、接続プールの切替、旧接続の解放を適用関数に実装してください。未実装関数は例外を投げ、未適用版の確認を防ぎます。快照から削除されたアカウントや取り消しイベントをアプリケーションの状態にも反映します。

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

func applyCredential(credential pam.Credential) error {
	return fmt.Errorf("implement connection validation, pool switching and old connection cleanup")
}
func restartApplication() error { return fmt.Errorf("implement application restart and health check") }
func handleCommand(ctx context.Context, client *pam.Client, event pam.Event) error {
	if event.Event == "application.restart.requested" {
		return restartApplication()
	}
	if event.Event != "credential.switch.requested" {
		return fmt.Errorf("unsupported application command")
	}
	credential, err := client.GetCredentialFresh(ctx, pam.CredentialSelector{Key: event.CredentialKey})
	if err != nil {
		return err
	}
	if credential.Revision != event.Revision || credential.Account.ID != event.AccountID {
		return fmt.Errorf("requested account version is superseded")
	}
	if err = applyCredential(credential); err != nil {
		return err
	}
	_, err = client.ConfirmCredential(ctx, credential.Key, credential.Revision, credential.Account.ID)
	return err
}
func main() {
	client, err := pam.NewClient(pam.Options{Endpoint: os.Getenv("JMS_ENDPOINT"), AppID: os.Getenv("JMS_APP_ID"), AppSecret: os.Getenv("JMS_APP_SECRET"), InstanceID: os.Getenv("JMS_INSTANCE_ID"), OrgID: os.Getenv("JMS_ORG_ID")})
	if err != nil {
		log.Fatal("Invalid SDK configuration")
	}
	defer client.Close()
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	err = client.WatchCredentialEvents(ctx, func(event pam.Event) error {
		if event.CommandID != "" {
			client.ExecuteApplicationCommand(ctx, event, func(command pam.Event) error { return handleCommand(ctx, client, command) })
			return nil
		}
		updates := []pam.Event{}
		if event.Event == "snapshot" {
			updates = event.Credentials
		} else if event.Event == "credential.updated" {
			updates = []pam.Event{event}
		}
		// On snapshots, remove application caches absent from the new authorized scope.
		for _, update := range updates {
			key := update.CredentialKey
			if key == "" {
				key = update.Key
			}
			selector := pam.CredentialSelector{}
			if update.CredentialMode == "subscription" && update.AccountID != "" && key != "" {
				if !strings.HasSuffix(key, ":"+update.AccountID) {
					key += ":" + update.AccountID
				}
				selector.Key = key
			} else if update.CredentialMode == "alternating_rotation" && key != "" {
				selector.Key = key
			} else {
				continue
			}
			credential, err := client.GetCredentialFresh(ctx, selector)
			if err != nil {
				return err
			}
			if err = applyCredential(credential); err != nil {
				return err
			}
			if update.CredentialMode == "alternating_rotation" {
				if _, err = client.ConfirmCredential(ctx, credential.Key, credential.Revision, credential.Account.ID); err != nil {
					return err
				}
			}
		}
		return nil
	})
	if err != nil && !errors.Is(err, context.Canceled) {
		log.Fatalf("Credential processing failed: %T", err)
	}
}
```

交互ローテーションでは実際の接続を検証し、接続プールを切り替えて古い接続を解放した後に、正確な key、revision、account_id を確認します。認証情報変更の購読では確認は不要です。接続検証に失敗した場合は確認してはいけません。

## アプリケーションコマンド

ポーリング、実行権の取得、結果報告は SDK のメソッドで行います。承認された実行権でのみハンドラーを実行します。切替では要求された版とアカウントを検証し、適用後に確認します。再起動では再起動と正常性確認を行い、完了後に成功を報告します。失敗報告のエラーは元の業務例外を置き換えません。

## 主なメソッド

- `GetCredential(ctx, CredentialSelector{Key: ...})`
- `GetCredential(ctx, CredentialSelector{AccountID: ...})`
- `GetCredentialFresh(ctx, selector)`
- `ConfirmCredential(ctx, key, revision, accountID)`
- `WatchEvents(ctx, EventHandlers{...}) / StartEvents(ctx, handlers)`
- `EventWatcher.Stop() / EventWatcher.Wait()`
- `WatchCredentialEvents(ctx, handler)`
- `ListApplicationCommands(ctx)`
- `ReportApplicationCommandResult(ctx, commandID, status, errorCode)`
- `ExecuteApplicationCommand(ctx, event, handler)`
- `SyncAgent(ctx, AgentSyncOptions{...})`
- `Clone() / Close()`

## トラブルシューティング

HTTP、ネットワーク、認証、デコードの失敗はエラーコードと HTTP 状態を含む SDK の例外・エラー型で通知されます。使用後はストリームとクライアントを閉じてください。複製クライアントのライフサイクルは独立しています。一時障害はアプリケーション側で再試行し、秘密情報や認証ヘッダーをログに記録しないでください。

`PAMError`

全 SDK はプロトコル版 1、Agent 設定はスキーマ版 1 を使用します。client_upgrade_required（HTTP 426）を受けたら互換性を確認し更新してください。未知の任意フィールドや通知イベントは許容しますが、未対応ポリシーは適用・確認できません。受領通知は自動送信され、認証情報の適用を証明しません。

## Go Agent の接続

認証には app_id、app_secret、org_id と安定した instance_id を使用し、認可範囲はアプリケーションに関連付けたポリシーに従います。すべてのパスとサービス操作はローカル設定です。state_file は最新パスワードを保持し、event_file は秘密を含まないイベント情報を追記します。delivery は既定の出力、rules はファイル、テンプレートと reload/restart または固定スクリプトを指定します。更新通知で最新値を取得・保存し、ファイルを原子的に置き換えてから操作を実行します。失敗は再試行します。rules の key には get_accounts の credentials[].key を使用します。購読 key にはアカウント ID が含まれます。空の rules は key ごとの既定ファイルを出力します。

ローカル rules でファイル、JSON/EnvironmentFile または信頼済みテンプレートと、systemd reload/restart や固定実行ファイルを設定します。スクリプトは標準入力で認証情報 JSON を受け取り、固定引数とタイムアウトを使い、適用を検証してから成功を返します。Core は実行パスや権限を拡張できません。設定変更後に Agent を再起動します。

認証には app_id、app_secret、org_id と安定した instance_id を使用し、認可範囲はアプリケーションに関連付けたポリシーに従います。すべてのパスとサービス操作はローカル設定です。state_file は最新パスワードを保持し、event_file は秘密を含まないイベント情報を追記します。delivery は既定の出力、rules はファイル、テンプレートと reload/restart または固定スクリプトを指定します。更新通知で最新値を取得・保存し、ファイルを原子的に置き換えてから操作を実行します。失敗は再試行します。rules の key には get_accounts の credentials[].key を使用します。購読 key にはアカウント ID が含まれます。空の rules は key ごとの既定ファイルを出力します。

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

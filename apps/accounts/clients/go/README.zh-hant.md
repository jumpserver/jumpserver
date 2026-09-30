# JumpServer PAM Go SDK

本 SDK 與 Python 憑證策略 SDK 對齊：取得授權帳號或輪換策略憑證、確認生效版本、監聽事件、處理應用程式指令及同步 Agent 狀態。請求 URL、HMAC 簽章、Digest、UTC 時間、請求 ID 與協定標頭均由客戶端自動產生。

## 環境需求

- Go 1.23+ / coder/websocket
- `cmd/demo/main.go`

## 設定與執行

安裝原始碼 SDK 並填寫下方設定。在應用程式管理中授權可 pull 的帳號；僅在需要 push 或輪換時綁定憑據策略。從接入資料取得應用程式 AK/SK 與組織 ID。替換預留值並保護身分資料，每個副本使用穩定且唯一的實例 ID。取密只能選擇帳號 ID 或策略 key 中的一種。

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

SDK 目前從本儲存庫原始碼安裝，尚未發佈至公開套件庫。將 /path/to/jumpserver 替換為絕對路徑；Go 和 Node.js 安裝命令在應用程式目錄執行，Java 相依套件加入應用程式 pom.xml。儲存庫範例的本地匯入應替換為下方套件匯入。

```bash
go mod edit -replace=github.com/jumpserver/jumpserver/apps/accounts/clients/go=/path/to/jumpserver/apps/accounts/clients/go
go get github.com/jumpserver/jumpserver/apps/accounts/clients/go@v0.0.0
```

```go
import pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
```

## 請求與回應

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

## 事件處理介面

先初始化本地帳號映射或連線池，再啟動監聽。Python 和 Node.js 使用子類別鉤子，Go 使用 EventHandlers，Java 使用 CredentialEventListener。必須實作範例中的連線切換函式；原有迭代器與回呼介面繼續保留。

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

首次與重連 snapshot、credential.updated 按策略模式取密，再循序呼叫憑據處理函式。讀取器和業務處理使用容量 128 的有界佇列；滿載時產生背壓。取密或處理失敗按 1–30 秒指數退避重試，每次重新取密。新事件替換同一目標的重試；快照重設範圍，撤銷與設定變更取消重試。處理須可重複執行。原始事件與撤銷鉤子不自動重試；指令仍須認領。received 僅表示已讀取，SDK 不自動確認輪換。較舊版本事件不會取消較新版本的取密重試。

`WatchEvents(ctx, handlers)` / `StartEvents(ctx, handlers)`; `Stop()` / `Wait()`; `context.CancelFunc`

WatchEvents 等待呼叫的 goroutine；StartEvents 不代表初始同步完成。每個客戶端只有一個高層監聽器。Stop 與 Close 請求取消，由外部 Wait 等待，勿在處理函式內 Wait。長操作須回應 context。

### 最新憑據與後端不可用

取密先請求 API。成功取得新憑據後替換本地保留值，舊版本不覆蓋新版本，且不按時間過期。僅在逾時、網路故障或 HTTP 5xx 時，返回相同查詢條件下已取得的最新憑據並標記本地來源；沒有保留值則拋出原始錯誤。SDK 在目前客戶端記憶體內保留，直到更新、撤銷或關閉；clone 與重新啟動不繼承。Agent 使用既有受保護的本地狀態保存。HTTP 401/403/404 或 client_upgrade_required 清空 SDK 保留值並報錯，成功回應格式錯誤也報錯。明確撤銷移除對應憑據；快照移除授權範圍外項目；設定變更先保留，由後續快照核對範圍。Agent 在 HTTP 同步前先執行明確撤銷或快照授權範圍縮小並保存範圍，後端故障期間或重新啟動後也會阻止相應本地取密。credential_not_found（HTTP 400）同樣清除 SDK 保留值。 以 account_id 直接 pull 一律需要即時 API 回應；push 快照不能證明快取的 pull 憑據仍獲授權。

- `credential.FromLocal`
- `GetCredentialFresh(ctx, selector)`

啟用高層監聽後，snapshot、credential.updated 自動取密、替換保留值，再呼叫業務函式。刷新失敗保留上一份並重試。Agent 也在更新通知後主動取密，後端故障時保留已有值。刷新與手動切換使用下方即時取得的呼叫；本地保留值不代表剛取得新版本，亦不自動確認輪換。

閒置時每 10 秒傳送應用層 ping，約 30 秒收不到訊息則重連，以 1–30 秒指數退避並重新簽章。快照恢復目前狀態，不重播歷史事件。



## 事件與憑證生效

處理首次/重新連線 snapshot 與 credential.updated。下方完整範例分別處理 subscription、alternating_rotation 及應用程式指令。實作憑證套用函式：驗證真實連線、切換連線池及釋放舊連線。預留函式會拋出例外，避免確認尚未套用的版本；應用程式本地狀態也須依快照移除已撤銷帳號並處理撤銷事件。

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

交替輪換需先驗證真實連線、切換應用程式連線池並釋放舊連線，再確認準確的 key、revision 和 account_id。憑證變更訂閱無需確認，連線驗證失敗時不得確認。

## 應用程式指令

輪詢、指令認領及結果回報均透過 SDK 方法完成，只有認領成功才執行處理函式。切換指令須驗證版本與帳號，套用後再確認；重新啟動指令須完成重啟及健康檢查。完成後才回報成功，失敗回報保留原始業務例外。

## 常用方法

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

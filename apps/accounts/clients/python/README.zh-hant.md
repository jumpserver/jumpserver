# JumpServer PAM Python SDK / Agent

Python 3.9+ 提供憑據策略 SDK。Go jms-pam-agent 無需 Python，可透過本機檔案、固定動作或本機 Socket 交付憑據。Linux、macOS 和 Windows 支援前景執行；內建 systemd 安裝僅支援 Linux。

<!-- agent-doc:start -->

## Go Agent 接入

準備具有 systemd 和應用程式使用者的 Linux 主機，從 Agent 接入精靈下載 jms_pam_agent.json。建置或取得 Go jms-pam-agent 二進位檔後安裝，使用穩定且唯一的執行個體 ID。本機設定為 /etc/jms-pam-agent/agent.json，服務固定為 jms-pam-agent.

```bash
cd apps/accounts/clients/go
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
chmod 0600 ./jms_pam_agent.json
sudo /usr/local/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

內建安裝需要 Linux/root。macOS、非 root Linux 或 Windows 請在接入精靈中選擇 JSON 或 Socket 交付，依照 init-local 與 run --local --config 命令執行。只初始化一次，後續重複使用產生的私有本機設定；前景模式不執行 systemd 動作。

`/etc/jms-pam-agent/agent.json`: `0600`; `state_file`, `event_file`, `delivery.delivery_root`, `delivery.socket_path`.

- JSON: `/opt/jumpserver-pam/credentials/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<credential-key>.env`
- Unix Socket: `/run/jms-pam-agent/agent.sock`

JSON 交付檔案，EnvironmentFile 對接固定 systemd 服務，Unix Socket 提供本地 API。Agent 在交付成功後儲存交付版本，應用程式驗證並使用後才儲存生效版本。Socket 屬於設定的應用程式使用者，權限為 0600，本地請求應以該使用者執行。

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<credential-key>.env
```

systemd unit 必須引用 EnvironmentFile。

本機 rules 設定目標檔案、JSON/EnvironmentFile 或可信範本，以及可選的 systemd reload/restart 或固定可執行腳本。腳本透過標準輸入接收憑據 JSON，參數固定、有逾時，並應在驗證業務生效後回報成功。Core 不能新增腳本路徑或擴大本機能力。修改私有設定後重新啟動 Agent。

下載的引導設定已包含 Agent 身分與交付設定。只需在 rules 中宣告業務使用的帳號 ID，再設定更新業務檔案、生效動作及執行中連線驗證。帳號設定 allow_account_switch 後可沿用同一規則處理 A/B 雙向輪換；可選 credential_check 於修改檔案前驗證新帳號。狀態、事件、Socket 路徑及 300 秒對帳週期皆有預設值。rules 為空時依憑據寫入預設檔案。

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


### 本地 API 與確認

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

交替輪換需先驗證真實連線、切換應用程式連線池並釋放舊連線，再確認準確的 key、revision 和 account_id。憑證變更訂閱無需確認，連線驗證失敗時不得確認。

```bash
/usr/local/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jms-pam-agent/agent.sock'
```

只有交替輪換需要 confirm。本地確認先持久化；confirmed 表示 Core 已接受，pending 表示之後重試。不能因為檔案寫入成功或服務重新啟動就確認。

### 問題排查

```bash
sudo systemctl start jms-pam-agent
sudo systemctl status jms-pam-agent --no-pager
sudo journalctl -u jms-pam-agent -n 100 --no-pager
sudo systemctl restart jms-pam-agent
```

Agent 在啟動、相關事件及每 300 秒同步。網路故障保留已取得的最新授權憑據；身分或授權被拒絕時阻止 Socket 取密，成功簽章同步後恢復。已交付檔案保留。SIGINT/SIGTERM 會關閉服務、連線及事件讀取執行緒。

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Python SDK 接入

建立並綁定憑證策略、授權資產帳號，從應用程式接入精靈下載 jms_pam_config.py。需要 Python 3.9+。執行下方儲存庫安裝指令，或在下載的 SDK 解壓目錄執行 python3 -m pip install .。

```bash
python3 -m pip install ./apps/accounts/clients/python
```

將 jms_pam_config.py 放在應用程式旁邊。client_options 包含應用程式身分資料，不要提交或寫入日誌。每個副本使用穩定且唯一的 instance_id。get_credential 只能提供一種選擇參數：帳號取密用 account_id，輪換策略用 key。

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


with Client(instance_id=instance_id, **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### 事件與憑證生效

同時處理首次/重新連線 snapshot 和 credential.updated。範例區分 subscription 與 alternating_rotation。實作 apply_credential 驗證真實連線、切換應用程式連線池並釋放舊連線；預留實作會拋出例外，防止確認尚未使用的憑證。

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def apply_credential(credential):
    raise NotImplementedError('請實作並驗證應用程式憑證切換')


with Client(instance_id=instance_id, **client_options) as client:
    for event in client.watch_credential_events():
        if event.get("event") == "snapshot":
            updates = event.get("credentials", [])
        elif event.get("event") == "credential.updated":
            updates = [event]
        else:
            continue
        for update in updates:
            mode = update.get("credential_mode")
            key = update.get("credential_key") or update.get("key")
            account_id = update.get("account_id")
            if mode == "subscription" and account_id and key:
                policy_key = key if key.endswith(f":{account_id}") else f"{key}:{account_id}"
                credential = client.get_credential(key=policy_key, allow_local_fallback=False)
            elif mode == "alternating_rotation" and key:
                credential = client.get_credential(key=key, allow_local_fallback=False)
            else:
                continue
            apply_credential(credential)
            if mode == "alternating_rotation":
                client.confirm_credential(
                    key=credential.key,
                    revision=credential.revision,
                    account_id=credential.account.id,
                )
```

交替輪換需先驗證真實連線、切換應用程式連線池並釋放舊連線，再確認準確的 key、revision 和 account_id。憑證變更訂閱無需確認，連線驗證失敗時不得確認。

SDK 在交出業務事件前自動盡力傳送 received 回執，應用程式無需額外傳送。回執僅表示已讀取事件，不表示憑證已經生效，也不能取代確認。應用程式應處理首次與重新連線快照；snapshot 和 pong 無需回執。

## 事件處理介面

先初始化本地帳號映射或連線池，再啟動監聽。Python 和 Node.js 使用子類別鉤子，Go 使用 EventHandlers，Java 使用 CredentialEventListener。必須實作範例中的連線切換函式；原有迭代器與回呼介面繼續保留。

```python
"""Subscription example using subclass hooks; demo.py retains the iterator API."""

from jms_pam import Client
from jms_pam_config import client_options


class MyClient(Client):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.credentials = {}

    def on_event(self, event):
        if event.get("event") == "snapshot":
            authorized_keys = {item["key"] for item in event.get("credentials", [])}
            for key in self.credentials.keys() - authorized_keys:
                # Also release this key's application connections.
                del self.credentials[key]

    def on_credential_changed(self, credential):
        # Validate and switch application connections using credential.asset and
        # credential.account. The handler must be safe to repeat on retry/reconnect.
        # Never log credential.account.secret or authentication headers.
        raise NotImplementedError("Implement the application connection update first")
        # Save only after the application has successfully switched connections:
        # self.credentials[credential.key] = credential

    def on_credential_revoked(self, event):
        self.credentials.pop(event.get("credential_key"), None)
        # Also release the affected application connections.


with MyClient(instance_id="order-service-node-1", **client_options) as client:
    client.watch_events()
```

首次與重連 snapshot、credential.updated 按策略模式取密，再循序呼叫憑據處理函式。讀取器和業務處理使用容量 128 的有界佇列；滿載時產生背壓。取密或處理失敗按 1–30 秒指數退避重試，每次重新取密。新事件替換同一目標的重試；快照重設範圍，撤銷與設定變更取消重試。處理須可重複執行。原始事件與撤銷鉤子不自動重試；指令仍須認領。received 僅表示已讀取，SDK 不自動確認輪換。較舊版本事件不會取消較新版本的取密重試。

`watch_events(stop_event=...)` / `start_events(stop_event=...)`; `stop_events()` / `close()`

watch_events 等待停止；start_events 不代表初始同步完成，服務須等待就緒。每個客戶端只有一個高層監聽器。stop_events 與 close 等待鉤子；鉤子可停止自己的客戶端。clone 重建子類別狀態。

### 最新憑據與後端不可用

取密先請求 API。成功取得新憑據後替換本地保留值，舊版本不覆蓋新版本，且不按時間過期。僅在逾時、網路故障或 HTTP 5xx 時，返回相同查詢條件下已取得的最新憑據並標記本地來源；沒有保留值則拋出原始錯誤。SDK 在目前客戶端記憶體內保留，直到更新、撤銷或關閉；clone 與重新啟動不繼承。Agent 使用既有受保護的本地狀態保存。HTTP 401/403/404 或 client_upgrade_required 清空 SDK 保留值並報錯，成功回應格式錯誤也報錯。明確撤銷移除對應憑據；快照移除授權範圍外項目；設定變更先保留，由後續快照核對範圍。Agent 在 HTTP 同步前先執行明確撤銷或快照授權範圍縮小並保存範圍，後端故障期間或重新啟動後也會阻止相應本地取密。credential_not_found（HTTP 400）同樣清除 SDK 保留值。 以 account_id 直接 pull 一律需要即時 API 回應；push 快照不能證明快取的 pull 憑據仍獲授權。

- `credential.from_local`
- `get_credential(key=..., allow_local_fallback=False)` / `get_credential(account_id=..., allow_local_fallback=False)`

啟用高層監聽後，snapshot、credential.updated 自動取密、替換保留值，再呼叫業務函式。刷新失敗保留上一份並重試。Agent 也在更新通知後主動取密，後端故障時保留已有值。刷新與手動切換使用下方即時取得的呼叫；本地保留值不代表剛取得新版本，亦不自動確認輪換。

閒置時每 10 秒傳送應用層 ping，約 30 秒收不到訊息則重連，以 1–30 秒指數退避並重新簽章。快照恢復目前狀態，不重播歷史事件。



### 應用程式指令

list_application_commands 輪詢待處理請求，execute_application_command(event, handler) 申請執行；只有 accepted 為 true 才執行處理函式。切換處理函式驗證請求帳號及版本、套用憑證並確認；重新啟動處理函式需檢查健康狀態，工作完成後才回報成功。失敗回報不會掩蓋原始例外。

### 常用方法

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `watch_events(stop_event=...)` / `start_events(stop_event=...)` / `stop_events()`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

with 或 close 關閉 HTTP 工作階段和事件串流，clone 建立獨立工作階段。HTTP、網路、驗證及解碼錯誤拋出 PAMError，包含 code、status_code、detail 和 original_error。在應用程式邊界重試暫時故障，明確處理授權拒絕，不記錄憑證。

新程式碼使用 snake_case 關鍵字方法和 dataclass 屬性。原 credential.v1 請求物件介面保留並發出 DeprecationWarning。SDK 和 Agent 使用相同的版本 1 協定，sync_agent 使用 KnownRevision 表示保留與交付版本。

<!-- sdk-doc:end -->

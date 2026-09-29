# JumpServer PAM Python SDK / Agent

Python 3.9+ 提供憑證策略 SDK 和 Linux Agent。SDK 使用應用程式 AK/SK；Agent 在本機交付憑證，其他語言的應用程式也可以讀取。

<!-- agent-doc:start -->

## Linux Agent 接入

準備具有 systemd、Python 3.9+ 和應用程式使用者的 Linux 主機。將應用程式綁定到憑證策略並授權帳號；交替輪換需授權兩個帳號。在應用程式接入精靈中選擇 Agent，設定執行使用者、安裝路徑及交付方式，下載 jms_pam_agent.json。安裝下載的 SDK 目錄，依下方預設路徑指令執行並替換預留位置。每個副本需有穩定且唯一的執行個體 ID。

```bash
sudo python3 -m venv /opt/jumpserver-pam/venv
sudo /opt/jumpserver-pam/venv/bin/python -m pip install '<sdk-directory>'
sudo /opt/jumpserver-pam/venv/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

預設路徑如下，configuration-id 來自引導檔案，credential-key 來自憑證策略；實際安裝路徑可能不同。引導檔案包含 AK/SK，應限制讀取權限，安裝後刪除下載的引導檔案，保護已安裝設定。

- JSON: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env`
- Unix Socket: `/run/jumpserver-pam/<configuration-id>/agent.sock`

JSON 交付檔案，EnvironmentFile 對接固定 systemd 服務，Unix Socket 提供本地 API。Agent 在交付成功後儲存交付版本，應用程式驗證並使用後才儲存生效版本。Socket 屬於設定的應用程式使用者，權限為 0600，本地請求應以該使用者執行。

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env
```

systemd unit 必須引用 EnvironmentFile。只有應用程式會重新讀取檔案時才使用 reload，reload 不會將新環境變數注入執行中的程序。安裝固定允許的路徑、使用者、服務和動作，擴大能力需重新安裝。

### 本地 API 與確認

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

交替輪換需先驗證真實連線、切換應用程式連線池並釋放舊連線，再確認準確的 key、revision 和 account_id。憑證變更訂閱無需確認，連線驗證失敗時不得確認。

```bash
/opt/jumpserver-pam/venv/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jumpserver-pam/<configuration-id>/agent.sock'
```

只有交替輪換需要 confirm。本地確認先持久化；confirmed 表示 Core 已接受，pending 表示之後重試。不能因為檔案寫入成功或服務重新啟動就確認。

### 問題排查

```bash
sudo systemctl status 'jms-pam-agent-<configuration-id>.service' --no-pager
sudo journalctl -u 'jms-pam-agent-<configuration-id>.service' -n 100 --no-pager
sudo systemctl restart 'jms-pam-agent-<configuration-id>.service'
```

Agent 在啟動、相關事件及每 300 秒同步。網路故障保留已授權快取；身分或授權被拒絕時阻止 Socket 取密，成功簽章同步後恢復。已交付檔案保留。SIGINT/SIGTERM 會關閉服務、連線及事件讀取執行緒。

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
from jms_pam_config import client_options


with Client(instance_id="app-node-1", **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### 事件與憑證生效

同時處理首次/重新連線 snapshot 和 credential.updated。範例區分 subscription 與 alternating_rotation。實作 apply_credential 驗證真實連線、切換應用程式連線池並釋放舊連線；預留實作會拋出例外，防止確認尚未使用的憑證。

```python
from jms_pam import Client
from jms_pam_config import client_options


def apply_credential(credential):
    raise NotImplementedError('請實作並驗證應用程式憑證切換')


with Client(instance_id="app-node-1", **client_options) as client:
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
            if mode == "subscription" and account_id:
                credential = client.get_credential(account_id=account_id)
            elif mode == "alternating_rotation" and key:
                credential = client.get_credential(key=key)
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

### 應用程式指令

list_application_commands 輪詢待處理請求，execute_application_command(event, handler) 申請執行；只有 accepted 為 true 才執行處理函式。切換處理函式驗證請求帳號及版本、套用憑證並確認；重新啟動處理函式需檢查健康狀態，工作完成後才回報成功。失敗回報不會掩蓋原始例外。

### 常用方法

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

with 或 close 關閉 HTTP 工作階段和事件串流，clone 建立獨立工作階段。HTTP、網路、驗證及解碼錯誤拋出 PAMError，包含 code、status_code、detail 和 original_error。在應用程式邊界重試暫時故障，明確處理授權拒絕，不記錄憑證。

新程式碼使用 snake_case 關鍵字方法和 dataclass 屬性。原 credential.v1 請求物件介面保留並發出 DeprecationWarning。SDK 和 Agent 使用相同的版本 1 協定，sync_agent 使用 KnownRevision 表示快取與交付版本。

<!-- sdk-doc:end -->

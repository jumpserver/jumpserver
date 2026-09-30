# cURL — 使用指南

本目錄提供舊 account-secret API 的 HTTP 簽章偵錯腳本。應用程式整合請使用 Python、Go、Java 或 Node.js SDK。

## 環境需求

- Bash / cURL / OpenSSL / base64
- `demo.sh`

指令碼需要 Bash、cURL、OpenSSL 和 base64。替換 ASSET 和 ACCOUNT，並確保簽章查詢參數與 cURL 實際傳送的編碼完全一致。

## 設定與執行

在應用程式管理中建立應用程式並授權目標資產帳號。填入下方端點、應用程式 AK/SK 和組織 ID；執行前將所有預留位置替換為實際值。

```bash
cd apps/accounts/clients/curl
export API_URL='https://jumpserver.example.com'
export API_KEY_ID='<app-id>'
export API_KEY_SECRET='<app-secret>'
export ORG_ID='<org-id>'

bash demo.sh
```

範例預設查詢資產 ubuntu_docker 和帳號 root，請改為實際授權名稱。以下指令從儲存庫根目錄開始執行。範例輸出包含密碼，不要傳送到應用程式日誌。

## 請求與回應

```http
GET /api/v1/accounts/integration-applications/account-secret/?asset=ubuntu_docker&account=root
```

```json
{"id":"<app-id>","secret":"<account-secret>"}
```

回應 id 表示應用程式身分，不表示帳號版本；secret 為 null 時可能受伺服器密碼檢視設定限制。這些範例不接收憑證事件、不回報生效版本，也不執行應用程式指令。

## 問題排查

401 時檢查 AK/SK、組織、主機時間及簽章 URL；403 時檢查應用程式狀態與帳號授權；400 時檢查資產/帳號選擇參數與 URL 編碼。不要記錄密碼或 Authorization 標頭，資產名及帳號名應符合獲授權資源。

## 憑證策略接入

下方簽章細節和協定表供偵錯參考。憑證策略透過 SDK 方法整合，也可透過 Go jms-pam-agent 的 JSON 檔案、EnvironmentFile 或 Unix Socket 整合。

| HTTP | API | JSON / query |
| --- | --- | --- |
| GET | `/api/v1/accounts/credential-client/credential/` | `instance_id`, `key` / `account_id` |
| POST | `/api/v1/accounts/credential-client/confirm/` | `instance_id`, `key`, `revision`, `account_id` |
| GET | `/api/v1/accounts/credential-client/commands/` | `instance_id` |
| POST | `/api/v1/accounts/credential-client/command-result/` | `instance_id`, `command_id`, `status`, `error_code` |
| WebSocket | `/ws/accounts/credential-events/` | `instance_id` |

依下方標頭順序計算 HMAC-SHA256 簽章。request-target 包含編碼後的路徑及查詢參數，Digest 使用實際請求本文的 SHA-256，X-JMS-Request-ID 使用唯一 UUID，Date 使用 HTTP UTC 時間；設定 X-JMS-Client-Version、X-JMS-Protocol-Version: 1 和 SDK 的 X-JMS-Config-Schema-Version: 0。API 與 WebSocket 都使用應用程式 AK/SK 和穩定、唯一的 instance_id，每次請求及重新連線重新產生簽章。

```text
(request-target) accept date digest x-jms-request-id x-jms-org
x-jms-client-version x-jms-protocol-version x-jms-config-schema-version
```

交替輪換需先驗證真實連線、切換應用程式連線池並釋放舊連線，再確認準確的 key、revision 和 account_id。憑證變更訂閱無需確認，連線驗證失敗時不得確認。

received 回執僅表示已讀取事件。處理帶 event_id 的業務事件前，在同一 WebSocket 傳送 received；snapshot 和 pong 無需回執。每次連線或重新連線都同步快照，處理 credential.updated，並回應授權撤銷及設定變更。

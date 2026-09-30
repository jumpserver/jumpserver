# JumpServer PAM Java SDK

本 SDK 與 Python 憑證策略 SDK 對齊：取得授權帳號或輪換策略憑證、確認生效版本、監聽事件、處理應用程式指令及同步 Agent 狀態。請求 URL、HMAC 簽章、Digest、UTC 時間、請求 ID 與協定標頭均由客戶端自動產生。

## 環境需求

- JDK 11+ / Maven / Jackson
- `src/main/java/org/jumpserver/pam/Demo.java`

## 設定與執行

安裝原始碼 SDK 並填寫下方設定。在應用程式管理中授權可 pull 的帳號；僅在需要 push 或輪換時綁定憑據策略。從接入資料取得應用程式 AK/SK 與組織 ID。替換預留值並保護身分資料，每個副本使用穩定且唯一的實例 ID。取密只能選擇帳號 ID 或策略 key 中的一種。

```bash
cd apps/accounts/clients/java
export JMS_ENDPOINT='https://jumpserver.example.com'
export JMS_APP_ID='<app-id>'
export JMS_APP_SECRET='<app-secret>'
export JMS_ORG_ID='<org-id>'
export JMS_INSTANCE_ID='app-node-1'
export JMS_ACCOUNT_ID='<account-id>'

mvn package dependency:copy-dependencies
java -cp 'target/classes:target/dependency/*' org.jumpserver.pam.Demo
```

SDK 目前從本儲存庫原始碼安裝，尚未發佈至公開套件庫。將 /path/to/jumpserver 替換為絕對路徑；Go 和 Node.js 安裝命令在應用程式目錄執行，Java 相依套件加入應用程式 pom.xml。儲存庫範例的本地匯入應替換為下方套件匯入。

```bash
mvn -f /path/to/jumpserver/apps/accounts/clients/java/pom.xml install
```

```xml
<dependency>
  <groupId>org.jumpserver</groupId>
  <artifactId>jms-pam</artifactId>
  <version>1.0.0</version>
</dependency>
```

```java
import org.jumpserver.pam.Client;
```

## 請求與回應

```java
package org.jumpserver.pam;

public final class Demo {
  public static void main(String[] args) {
    Client.Options options =
        new Client.Options(
                System.getenv("JMS_ENDPOINT"),
                System.getenv("JMS_APP_ID"),
                System.getenv("JMS_APP_SECRET"),
                System.getenv("JMS_INSTANCE_ID"))
            .orgId(System.getenv("JMS_ORG_ID"));
    try (Client client = new Client(options)) {
      Models.Credential credential =
          client.getCredentialByAccountId(System.getenv("JMS_ACCOUNT_ID"));
      // Pass credential.getAccount().getUsername() / getSecret() to the connection pool.
      System.out.println(
          "Fetched revision "
              + credential.getRevision()
              + "; implement application credential switching.");
    }
  }
}
```

## 事件處理介面

先初始化本地帳號映射或連線池，再啟動監聽。Python 和 Node.js 使用子類別鉤子，Go 使用 EventHandlers，Java 使用 CredentialEventListener。必須實作範例中的連線切換函式；原有迭代器與回呼介面繼續保留。

```java
package org.jumpserver.pam;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.jumpserver.pam.Models.Credential;
import org.jumpserver.pam.Models.Event;

/** Replace the business hook before running. Listener methods run serially. */
public final class HooksDemo implements CredentialEventListener {
  private final Client client;
  private final Map<String, Credential> credentials = new HashMap<>();
  private final Map<String, String> modes = new HashMap<>();

  public HooksDemo(Client client) {
    this.client = client;
  }

  @Override
  public void onEvent(Event event) {
    List<Event> updates = List.of(event);
    if (event.getEvent().equals("snapshot")) {
      modes.clear();
      updates = event.getCredentials();
    }
    if (event.getEvent().equals("snapshot") || event.getEvent().equals("credential.updated"))
      for (Event update : updates) modes.put(update.getKey(), update.getCredentialMode());
    if (event.getEvent().equals("snapshot"))
      credentials.keySet().removeIf(key -> !modes.containsKey(key)); // Also release connections.
    // Use executeApplicationCommand for commands; see EventsDemo.
  }

  @Override
  public void onCredentialChanged(Credential credential) {
    applyCredential(credential);
    if ("alternating_rotation".equals(modes.get(credential.getKey())))
      client.confirmCredential(
          credential.getKey(), credential.getRevision(), credential.getAccount().getId());
    credentials.put(credential.getKey(), credential);
  }

  private void applyCredential(Credential credential) {
    throw new UnsupportedOperationException(
        "Implement connection validation, pool switching and old connection cleanup");
  }

  @Override
  public void onCredentialRevoked(Event event) {
    credentials.remove(event.getKey()); // Also release affected connections.
  }

  public static void main(String[] args) throws InterruptedException {
    Client.Options options =
        new Client.Options(
                System.getenv("JMS_ENDPOINT"),
                System.getenv("JMS_APP_ID"),
                System.getenv("JMS_APP_SECRET"),
                System.getenv("JMS_INSTANCE_ID"))
            .orgId(System.getenv("JMS_ORG_ID"));
    try (Client client = new Client(options)) {
      Thread stop = new Thread(client::close, "jms-pam-shutdown");
      Runtime.getRuntime().addShutdownHook(stop);
      try {
        client.watchEvents(new HooksDemo(client));
      } finally {
        try {
          Runtime.getRuntime().removeShutdownHook(stop);
        } catch (IllegalStateException ignored) {
        }
      }
    }
  }
}
```

首次與重連 snapshot、credential.updated 按策略模式取密，再循序呼叫憑據處理函式。讀取器和業務處理使用容量 128 的有界佇列；滿載時產生背壓。取密或處理失敗按 1–30 秒指數退避重試，每次重新取密。新事件替換同一目標的重試；快照重設範圍，撤銷與設定變更取消重試。處理須可重複執行。原始事件與撤銷鉤子不自動重試；指令仍須認領。received 僅表示已讀取，SDK 不自動確認輪換。較舊版本事件不會取消較新版本的取密重試。

`watchEvents(listener)` / `startEvents(listener)`; `stop()` / `close()` / `awaitTermination()`

watchEvents 等待呼叫執行緒；startEvents 不代表初始同步完成。每個客戶端只有一個高層監聽器。訂閱與客戶端 close 會等待處理完成；鉤子可自行 close，awaitTermination 須由外部呼叫。

### 最新憑據與後端不可用

取密先請求 API。成功取得新憑據後替換本地保留值，舊版本不覆蓋新版本，且不按時間過期。僅在逾時、網路故障或 HTTP 5xx 時，返回相同查詢條件下已取得的最新憑據並標記本地來源；沒有保留值則拋出原始錯誤。SDK 在目前客戶端記憶體內保留，直到更新、撤銷或關閉；clone 與重新啟動不繼承。Agent 使用既有受保護的本地狀態保存。HTTP 401/403/404 或 client_upgrade_required 清空 SDK 保留值並報錯，成功回應格式錯誤也報錯。明確撤銷移除對應憑據；快照移除授權範圍外項目；設定變更先保留，由後續快照核對範圍。Agent 在 HTTP 同步前先執行明確撤銷或快照授權範圍縮小並保存範圍，後端故障期間或重新啟動後也會阻止相應本地取密。credential_not_found（HTTP 400）同樣清除 SDK 保留值。 以 account_id 直接 pull 一律需要即時 API 回應；push 快照不能證明快取的 pull 憑據仍獲授權。

- `credential.isFromLocal()`
- `getCredential(key, false)` / `getCredentialByAccountId(accountId, false)`

啟用高層監聽後，snapshot、credential.updated 自動取密、替換保留值，再呼叫業務函式。刷新失敗保留上一份並重試。Agent 也在更新通知後主動取密，後端故障時保留已有值。刷新與手動切換使用下方即時取得的呼叫；本地保留值不代表剛取得新版本，亦不自動確認輪換。

閒置時每 10 秒傳送應用層 ping，約 30 秒收不到訊息則重連，以 1–30 秒指數退避並重新簽章。快照恢復目前狀態，不重播歷史事件。



## 事件與憑證生效

處理首次/重新連線 snapshot 與 credential.updated。下方完整範例分別處理 subscription、alternating_rotation 及應用程式指令。實作憑證套用函式：驗證真實連線、切換連線池及釋放舊連線。預留函式會拋出例外，避免確認尚未套用的版本；應用程式本地狀態也須依快照移除已撤銷帳號並處理撤銷事件。

```java
package org.jumpserver.pam;

import java.util.List;
import org.jumpserver.pam.Models.Credential;
import org.jumpserver.pam.Models.Event;

/** Replace the business hooks before running; unapplied credentials are never confirmed. */
public final class EventsDemo {
  private static void applyCredential(Credential credential) {
    throw new UnsupportedOperationException(
        "Implement connection validation, pool switching and old connection cleanup");
  }

  private static void restartApplication() {
    throw new UnsupportedOperationException("Implement restart and health check");
  }

  private static void handleCommand(Client client, Event event) {
    if (event.getEvent().equals("application.restart.requested")) {
      restartApplication();
      return;
    }
    if (!event.getEvent().equals("credential.switch.requested"))
      throw new IllegalArgumentException("Unsupported application command");
    Credential credential = client.getCredential(event.getKey(), false);
    if (credential.getRevision() != event.getRevision()
        || !credential.getAccount().getId().equals(event.getAccountId()))
      throw new IllegalArgumentException("Requested account version is superseded");
    applyCredential(credential);
    client.confirmCredential(
        credential.getKey(), credential.getRevision(), credential.getAccount().getId());
  }

  public static void main(String[] args) {
    Client.Options options =
        new Client.Options(
                System.getenv("JMS_ENDPOINT"),
                System.getenv("JMS_APP_ID"),
                System.getenv("JMS_APP_SECRET"),
                System.getenv("JMS_INSTANCE_ID"))
            .orgId(System.getenv("JMS_ORG_ID"));
    try (Client client = new Client(options)) {
      Thread stop = new Thread(client::close, "jms-pam-shutdown");
      Runtime.getRuntime().addShutdownHook(stop);
      try (EventStream stream = client.watchCredentialEvents()) {
        for (Event event : stream) {
          if (!event.getCommandId().isEmpty()) {
            try {
              client.executeApplicationCommand(event, command -> handleCommand(client, command));
            } catch (RuntimeException ignored) {
            }
            continue;
          }
          List<Event> updates =
              event.getEvent().equals("snapshot")
                  ? event.getCredentials()
                  : event.getEvent().equals("credential.updated") ? List.of(event) : List.of();
          // On snapshots, remove application caches absent from the new authorized scope.
          for (Event update : updates) {
            Credential credential;
            if (update.getCredentialMode().equals("subscription")
                && !update.getAccountId().isEmpty() && !update.getKey().isEmpty()) {
              String key = update.getKey();
              if (!key.endsWith(":" + update.getAccountId())) key += ":" + update.getAccountId();
              credential = client.getCredential(key, false);
            }
            else if (update.getCredentialMode().equals("alternating_rotation")
                && !update.getKey().isEmpty())
              credential = client.getCredential(update.getKey(), false);
            else continue;
            applyCredential(credential);
            if (update.getCredentialMode().equals("alternating_rotation"))
              client.confirmCredential(
                  credential.getKey(), credential.getRevision(), credential.getAccount().getId());
          }
        }
      } finally {
        try {
          Runtime.getRuntime().removeShutdownHook(stop);
        } catch (IllegalStateException ignored) {
          // The shutdown hook is already closing the client.
        }
      }
    }
  }
}
```

交替輪換需先驗證真實連線、切換應用程式連線池並釋放舊連線，再確認準確的 key、revision 和 account_id。憑證變更訂閱無需確認，連線驗證失敗時不得確認。

## 應用程式指令

輪詢、指令認領及結果回報均透過 SDK 方法完成，只有認領成功才執行處理函式。切換指令須驗證版本與帳號，套用後再確認；重新啟動指令須完成重啟及健康檢查。完成後才回報成功，失敗回報保留原始業務例外。

## 常用方法

- `getCredential(key)`
- `getCredentialByAccountId(accountId)`
- `getCredential(key, false) / getCredentialByAccountId(accountId, false)`
- `confirmCredential(key, revision, accountId)`
- `watchCredentialEvents()`
- `watchEvents(listener) / startEvents(listener)`
- `EventSubscription.stop() / close() / awaitTermination()`
- `listApplicationCommands()`
- `reportApplicationCommandResult(commandId, status, errorCode)`
- `executeApplicationCommand(event, handler)`
- `syncAgent(credentials, deliveredCredentials, configDigest, syncStatus, syncError)`
- `clone() / close()`

## 問題排查

HTTP、網路、認證及解碼錯誤使用 SDK 例外或錯誤類型，包含錯誤碼與 HTTP 狀態。使用完畢後關閉事件流與客戶端，複製客戶端具有獨立生命週期。在業務邊界重試暫時故障，不記錄密碼或認證標頭。

`PAMException`

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

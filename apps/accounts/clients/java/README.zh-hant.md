# JumpServer PAM Java SDK

本 SDK 與 Python 憑證策略 SDK 對齊：取得授權帳號或輪換策略憑證、確認生效版本、監聽事件、處理應用程式指令及同步 Agent 狀態。請求 URL、HMAC 簽章、Digest、UTC 時間、請求 ID 與協定標頭均由客戶端自動產生。

## 環境需求

- JDK 11+ / Maven / Jackson
- `src/main/java/org/jumpserver/pam/Demo.java`

## 設定與執行

安裝原始碼 SDK 並填寫下方設定。在應用程式管理中授權帳號及綁定策略，從接入資料取得應用程式 AK/SK 與組織 ID。替換預留值並保護身分資料，每個副本使用穩定且唯一的實例 ID。取密只能選擇帳號 ID 或策略 key 中的一種。

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

## 事件與憑證生效

處理首次/重新連線 snapshot 與 credential.updated。下方完整範例分別處理 subscription、alternating_rotation 及應用程式指令。實作憑證套用函式：驗證真實連線、切換連線池及釋放舊連線。預留函式會拋出例外，避免確認尚未套用的版本；快取也須依快照移除已撤銷帳號並處理撤銷事件。

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
    Credential credential = client.getCredential(event.getKey());
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
                && !update.getAccountId().isEmpty())
              credential = client.getCredentialByAccountId(update.getAccountId());
            else if (update.getCredentialMode().equals("alternating_rotation")
                && !update.getKey().isEmpty()) credential = client.getCredential(update.getKey());
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
- `confirmCredential(key, revision, accountId)`
- `watchCredentialEvents()`
- `listApplicationCommands()`
- `reportApplicationCommandResult(commandId, status, errorCode)`
- `executeApplicationCommand(event, handler)`
- `syncAgent(credentials, deliveredCredentials, configDigest, syncStatus, syncError)`
- `clone() / close()`

## 問題排查

HTTP、網路、認證及解碼錯誤使用 SDK 例外或錯誤類型，包含錯誤碼與 HTTP 狀態。使用完畢後關閉事件流與客戶端，複製客戶端具有獨立生命週期。在業務邊界重試暫時故障，不記錄密碼或認證標頭。

`PAMException`

各 SDK 使用版本 1 協定，Agent 設定格式為版本 1。收到 client_upgrade_required（HTTP 426）時檢查相容性並升級。允許未知可選欄位及通知事件，未實作的策略類型不得套用或確認。SDK 自動傳送接收回執，不能作為憑證已生效的證明。

## Linux Agent 接入

Agent 同步方法供 Agent 實作共用，需要 Agent 身分或 source 與設定 ID，以 KnownRevision 回報快取及交付版本。目前 Linux 安裝、檔案交付與本地 API 由 Python Agent 提供，各程式語言的應用程式均可使用。

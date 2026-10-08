# JumpServer PAM Java SDK

本 SDK は Python の認証情報ポリシー SDK と同じ機能を提供します。許可されたアカウントやローテーションポリシーの認証情報取得、適用済み版の確認、イベント購読、アプリケーションコマンド処理、Agent 同期を行います。URL、HMAC 署名、Digest、UTC 日時、リクエスト ID、プロトコルヘッダーは自動生成されます。

## 動作要件

- JDK 11+ / Maven / Jackson
- `src/main/java/org/jumpserver/pam/Demo.java`

## 設定と実行

ソース SDK をインストールし、下記を設定します。アプリケーション管理で pull 対象のアカウントを許可し、push またはローテーションが必要な場合だけポリシーを関連付けます。接続資料から AK/SK と組織 ID を取得してください。プレースホルダーを置き換え、認証資料を安全に保管します。各レプリカには安定した一意のインスタンス ID を使い、取得にはアカウント ID またはポリシー key の一方だけを指定します。

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

SDK は現在このリポジトリのソースからインストールし、公開パッケージレジストリには未公開です。/path/to/jumpserver を絶対パスに置き換えます。Go と Node.js のインストールはアプリケーションのディレクトリで実行し、Java の依存関係は pom.xml に追加します。リポジトリの実行例のローカルインポートは以下のパッケージインポートに置き換えてください。

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

## リクエストとレスポンス

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

## イベントハンドラー

ローカル状態を初期化してから監視を開始します。Python と Node.js はサブクラス、Go は EventHandlers、Java は CredentialEventListener を使用します。例の接続切替処理を実装してください。従来の API も利用できます。

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

初回・再接続の snapshot と credential.updated はモード別に認証情報を取得し、ハンドラーを順番に呼び出します。受信と処理は上限 128 件のキューで接続され、満杯時は受信を待機します。取得・適用の失敗は 1–30 秒の指数バックオフで再試行し、毎回取得し直します。同じ対象の更新は再試行を置換し、snapshot は範囲を更新、失効・設定変更は再試行を解除します。処理は繰り返し可能にしてください。観測・失効フックは自動再試行しません。コマンドは実行権の取得が必要です。received は受信のみを示し、SDK はローテーションを自動確認しません。古いリビジョンのイベントは、新しいリビジョンの取得の再試行を取り消しません。

`watchEvents(listener)` / `startEvents(listener)`; `stop()` / `close()` / `awaitTermination()`

watchEvents は呼出元スレッドで待ちます。startEvents は同期完了を保証しません。監視は 1 つです。close は処理終了を待ち、ハンドラー自身からも close できます。awaitTermination は外部から呼びます。

### 最新の認証情報とバックエンド障害

取得はまず API を呼びます。取得成功時に保持値を更新し、古いバージョンで新しい値を上書きせず、時間による有効期限も設けません。タイムアウト、ネットワーク障害、HTTP 5xx の場合だけ、同じ検索条件の最後に取得した値をローカル由来のフラグ付きで返します。保持値がなければ元のエラーです。SDK は更新・失効・終了までクライアントのメモリに保持し、clone や再起動は空から始まります。Agent は保護された既存のローカル状態に保存します。HTTP 401/403/404 または client_upgrade_required は SDK の保持値を消去して失敗し、不正な成功応答も失敗します。失効は対象を、snapshot は認可範囲外を削除します。設定変更時は次の snapshot で範囲を確認するまで保持します。Agent は HTTP 同期の前に明示的な取り消しと snapshot の範囲縮小を適用して保存し、バックエンド障害中や再起動後も該当するローカル取得を停止します。credential_not_found（HTTP 400）でも SDK の保持値を削除します。 account_id による直接 pull には常にライブ API 応答が必要です。push の snapshot はキャッシュされた pull 認可を示しません。

- `credential.isFromLocal()`
- `getCredential(key, false)` / `getCredentialByAccountId(accountId, false)`

管理された監視を有効にすると、snapshot と credential.updated が自動で取得し、保持値を更新してから業務フックを呼びます。更新失敗時は前の値を保持し再試行します。Agent も更新通知で取得し、障害時は既存値を保持します。更新や手動切替には下記の API 取得必須の呼び出しを使用してください。保持値を新しく取得したバージョンと見なしたり、ローテーションを自動確認したりしません。

アイドル時は 10 秒ごとに ping を送り、約 30 秒メッセージがなければ再接続します。待機は 1–30 秒の指数バックオフで毎回再署名します。snapshot は現在の状態を復元し、履歴イベントは再送しません。



## イベントと認証情報の適用

初回・再接続 snapshot と credential.updated を処理します。下記の完全な例は subscription、alternating_rotation、アプリケーションコマンドを扱います。実接続の検証、接続プールの切替、旧接続の解放を適用関数に実装してください。未実装関数は例外を投げ、未適用版の確認を防ぎます。快照から削除されたアカウントや取り消しイベントをアプリケーションの状態にも反映します。

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

交互ローテーションでは実際の接続を検証し、接続プールを切り替えて古い接続を解放した後に、正確な key、revision、account_id を確認します。認証情報変更の購読では確認は不要です。接続検証に失敗した場合は確認してはいけません。

## アプリケーションコマンド

ポーリング、実行権の取得、結果報告は SDK のメソッドで行います。承認された実行権でのみハンドラーを実行します。切替では要求された版とアカウントを検証し、適用後に確認します。再起動では再起動と正常性確認を行い、完了後に成功を報告します。失敗報告のエラーは元の業務例外を置き換えません。

## 主なメソッド

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

## トラブルシューティング

HTTP、ネットワーク、認証、デコードの失敗はエラーコードと HTTP 状態を含む SDK の例外・エラー型で通知されます。使用後はストリームとクライアントを閉じてください。複製クライアントのライフサイクルは独立しています。一時障害はアプリケーション側で再試行し、秘密情報や認証ヘッダーをログに記録しないでください。

`PAMException`

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

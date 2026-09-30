# JumpServer PAM Java SDK

이 SDK는 Python 자격 증명 정책 SDK와 기능을 맞춥니다. 허용된 계정 또는 순환 정책의 자격 증명 조회, 적용 버전 확인, 이벤트 구독, 애플리케이션 명령 처리와 Agent 동기화를 제공합니다. URL, HMAC 서명, Digest, UTC 시간, 요청 ID와 프로토콜 헤더는 자동 생성됩니다.

## 환경 요구 사항

- JDK 11+ / Maven / Jackson
- `src/main/java/org/jumpserver/pam/Demo.java`

## 설정 및 실행

소스 SDK를 설치하고 아래 설정을 입력하세요. 애플리케이션 관리에서 pull 대상 계정을 허용하고, push 또는 순환이 필요한 경우에만 정책을 연결합니다. 접속 자료에서 AK/SK와 조직 ID를 가져옵니다. 자리표시자를 교체하고 인증 자료를 안전하게 보관하세요. 복제본마다 안정적이고 고유한 인스턴스 ID를 사용하며 계정 ID 또는 정책 key 중 하나만 지정합니다.

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

SDK는 현재 이 저장소의 소스로 설치하며 공개 패키지 저장소에는 배포되지 않았습니다. /path/to/jumpserver를 절대 경로로 바꾸세요. Go와 Node.js 설치 명령은 애플리케이션 디렉터리에서 실행하고 Java 의존성은 애플리케이션 pom.xml에 추가하세요. 저장소 예제의 로컬 가져오기는 아래 패키지 가져오기로 바꾸세요.

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

## 요청 및 응답

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

## 이벤트 처리기

로컬 상태를 초기화한 뒤 감시를 시작합니다. Python과 Node.js는 서브클래스, Go는 EventHandlers, Java는 CredentialEventListener를 사용합니다. 예제의 실제 연결 전환을 구현해야 합니다. 기존 API도 유지됩니다.

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

초기 및 재연결 snapshot과 credential.updated는 모드별로 자격 증명을 조회하고 처리기를 순차 호출합니다. 읽기와 업무 처리는 최대 128개 큐를 사용하며 가득 차면 역압력이 발생합니다. 조회 또는 적용 실패는 1–30초 지수 백오프로 재시도하며 매번 다시 조회합니다. 같은 대상의 새 이벤트는 재시도를 대체하고, snapshot은 범위를 재설정하며 취소와 구성 변경은 재시도를 제거합니다. 처리는 반복 가능해야 합니다. 관찰 및 취소 훅은 자동 재시도하지 않으며 명령은 실행 권한을 먼저 요청해야 합니다. received는 수신만 의미하며 SDK는 회전을 자동 확인하지 않습니다.이전 버전의 이벤트는 최신 버전 조회의 대기 중인 재시도를 취소하지 않습니다.

`watchEvents(listener)` / `startEvents(listener)`; `stop()` / `close()` / `awaitTermination()`

watchEvents는 호출 스레드에서 기다립니다. startEvents는 초기 동기화 완료를 보장하지 않습니다. 감시는 하나만 허용됩니다. close는 처리 종료를 기다리며 훅 안에서도 닫을 수 있습니다. awaitTermination은 외부에서 호출하세요.

### 최신 자격 증명과 백엔드 장애

먼저 API를 요청합니다. 성공하면 보유한 최신 값을 교체하며 오래된 버전으로 새 값을 덮어쓰지 않고 시간 만료도 없습니다. 시간 초과, 네트워크 오류 또는 HTTP 5xx일 때만 같은 선택자의 마지막 성공 값을 로컬 표시와 함께 반환합니다. 이전 값이 없으면 원래 오류입니다. SDK는 업데이트, 취소 또는 종료까지 클라이언트 메모리에 보유하며 clone과 재시작은 빈 상태로 시작합니다. Agent는 기존의 보호된 로컬 상태에 저장합니다. HTTP 401/403/404 또는 client_upgrade_required는 SDK 값을 삭제하고 실패하며 잘못된 성공 응답도 실패합니다. 취소는 해당 값을, snapshot은 권한 범위 밖 값을 삭제합니다. 구성 변경은 다음 snapshot으로 범위를 확인할 때까지 보유합니다.Agent는 HTTP 동기화 전에 명시적 취소와 snapshot 범위 축소를 적용하고 저장하며, 백엔드 장애 중이나 재시작 후에도 해당 로컬 조회를 차단합니다.credential_not_found(HTTP 400) 응답도 SDK 보관 값을 삭제합니다. account_id로 직접 pull하려면 항상 실시간 API 응답이 필요합니다. push 스냅샷은 캐시된 pull 권한을 증명하지 않습니다.

- `credential.isFromLocal()`
- `getCredential(key, false)` / `getCredentialByAccountId(accountId, false)`

관리된 감시를 켜면 snapshot과 credential.updated가 자동 조회하고 보유 값을 교체한 뒤 업무 훅을 호출합니다. 실패하면 이전 값을 유지하고 재시도합니다. Agent도 업데이트 알림으로 조회하며 장애 시 이전 값을 유지합니다. 업데이트와 수동 전환에는 아래 API 조회 필수 호출을 사용하세요. 보유 값은 새로 조회한 버전이 아니며 회전을 자동 확인하지 않습니다.

유휴 시 10초마다 ping을 보내고 약 30초간 메시지가 없으면 재연결합니다. 1–30초 지수 백오프와 새 서명을 사용합니다. snapshot은 현재 상태를 복원하며 과거 이벤트를 재생하지 않습니다.



## 이벤트 및 자격 증명 적용

최초/재연결 snapshot과 credential.updated를 처리합니다. 아래 전체 예제는 subscription, alternating_rotation 및 애플리케이션 명령을 처리합니다. 실제 연결 검증, 연결 풀 전환과 이전 연결 해제를 적용 함수에 구현하세요. 미구현 함수는 예외를 발생시켜 적용하지 않은 버전의 확인을 막습니다. 스냅샷에서 제거된 계정과 권한 취소 이벤트도 애플리케이션 상태에 반영해야 합니다.

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

교대 회전에서는 실제 연결을 검증하고 연결 풀을 바꾸며 기존 연결을 해제한 뒤 정확한 key, revision, account_id를 확인하세요. 자격 증명 변경 구독은 확인이 필요 없습니다. 연결 검증에 실패하면 확인하면 안 됩니다.

## 애플리케이션 명령

폴링, 명령 실행 권한 요청과 결과 보고는 SDK 메서드로 수행합니다. 실행 요청이 수락된 경우에만 핸들러가 동작합니다. 전환 명령은 요청 버전과 계정을 검사하고 적용 후 확인하며, 재시작 명령은 재시작과 상태 검사를 마쳐야 합니다. 완료 후에만 성공을 보고하며 실패 보고 오류는 원래 업무 예외를 덮어쓰지 않습니다.

## 주요 메서드

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

## 문제 해결

HTTP, 네트워크, 인증 및 디코딩 실패는 코드와 HTTP 상태를 포함한 SDK 예외/오류 형식을 사용합니다. 사용 후 스트림과 클라이언트를 닫으세요. 복제 클라이언트의 수명은 독립적입니다. 일시적 실패는 애플리케이션 경계에서 재시도하고 비밀이나 인증 헤더는 기록하지 마세요.

`PAMException`

모든 SDK는 프로토콜 버전 1을, Agent 설정은 스키마 버전 1을 사용합니다. client_upgrade_required(HTTP 426)를 받으면 호환성을 확인하고 업그레이드하세요. 알 수 없는 선택 필드와 알림 이벤트는 허용하지만 지원하지 않는 정책은 적용하거나 확인하면 안 됩니다. 수신 확인은 자동 전송되며 자격 증명 적용을 증명하지 않습니다.

## Go Agent 연동

인증에는 app_id, app_secret, org_id 및 안정적인 instance_id를 사용하며 권한은 애플리케이션에 연결된 정책을 따릅니다. 경로와 서비스 동작은 모두 로컬 설정입니다. state_file은 최신 암호를 유지하고 event_file은 비밀 없는 이벤트 정보를 추가합니다. delivery는 기본 출력을, rules는 파일, 템플릿 및 reload/restart 또는 고정 스크립트를 지정합니다. 업데이트 알림을 받으면 최신 암호를 가져와 저장하고 파일을 원자적으로 교체한 뒤 동작을 실행합니다. 실패는 재시도합니다. rules에는 get_accounts의 credentials[].key를 사용합니다. 구독 key에는 계정 ID가 포함됩니다. rules가 비어 있으면 key별 기본 파일을 씁니다.

로컬 rules에 파일, JSON/EnvironmentFile 또는 신뢰할 수 있는 템플릿과 systemd reload/restart 또는 고정 실행 파일을 설정합니다. 스크립트는 표준 입력으로 자격 증명 JSON을 받고 고정 인수와 제한 시간을 사용하며 적용을 검증한 후 성공합니다. Core는 실행 경로나 권한을 확장할 수 없습니다. 구성을 수정한 후 Agent를 재시작합니다.

인증에는 app_id, app_secret, org_id 및 안정적인 instance_id를 사용하며 권한은 애플리케이션에 연결된 정책을 따릅니다. 경로와 서비스 동작은 모두 로컬 설정입니다. state_file은 최신 암호를 유지하고 event_file은 비밀 없는 이벤트 정보를 추가합니다. delivery는 기본 출력을, rules는 파일, 템플릿 및 reload/restart 또는 고정 스크립트를 지정합니다. 업데이트 알림을 받으면 최신 암호를 가져와 저장하고 파일을 원자적으로 교체한 뒤 동작을 실행합니다. 실패는 재시도합니다. rules에는 get_accounts의 credentials[].key를 사용합니다. 구독 key에는 계정 ID가 포함됩니다. rules가 비어 있으면 key별 기본 파일을 씁니다.

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

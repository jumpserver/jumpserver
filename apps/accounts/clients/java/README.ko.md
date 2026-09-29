# JumpServer PAM Java SDK

이 SDK는 Python 자격 증명 정책 SDK와 기능을 맞춥니다. 허용된 계정 또는 순환 정책의 자격 증명 조회, 적용 버전 확인, 이벤트 구독, 애플리케이션 명령 처리와 Agent 동기화를 제공합니다. URL, HMAC 서명, Digest, UTC 시간, 요청 ID와 프로토콜 헤더는 자동 생성됩니다.

## 환경 요구 사항

- JDK 11+ / Maven / Jackson
- `src/main/java/org/jumpserver/pam/Demo.java`

## 설정 및 실행

소스 SDK를 설치하고 아래 설정을 입력하세요. 애플리케이션 관리에서 계정을 허용하고 정책을 연결한 뒤 접속 자료에서 AK/SK와 조직 ID를 가져옵니다. 자리표시자를 교체하고 인증 자료를 안전하게 보관하세요. 복제본마다 안정적이고 고유한 인스턴스 ID를 사용하며 계정 ID 또는 정책 key 중 하나만 지정합니다.

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

## 이벤트 및 자격 증명 적용

최초/재연결 snapshot과 credential.updated를 처리합니다. 아래 전체 예제는 subscription, alternating_rotation 및 애플리케이션 명령을 처리합니다. 실제 연결 검증, 연결 풀 전환과 이전 연결 해제를 적용 함수에 구현하세요. 미구현 함수는 예외를 발생시켜 적용하지 않은 버전의 확인을 막습니다. 스냅샷에서 제거된 계정과 권한 취소 이벤트도 애플리케이션 캐시에 반영해야 합니다.

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

교대 회전에서는 실제 연결을 검증하고 연결 풀을 바꾸며 기존 연결을 해제한 뒤 정확한 key, revision, account_id를 확인하세요. 자격 증명 변경 구독은 확인이 필요 없습니다. 연결 검증에 실패하면 확인하면 안 됩니다.

## 애플리케이션 명령

폴링, 명령 실행 권한 요청과 결과 보고는 SDK 메서드로 수행합니다. 실행 요청이 수락된 경우에만 핸들러가 동작합니다. 전환 명령은 요청 버전과 계정을 검사하고 적용 후 확인하며, 재시작 명령은 재시작과 상태 검사를 마쳐야 합니다. 완료 후에만 성공을 보고하며 실패 보고 오류는 원래 업무 예외를 덮어쓰지 않습니다.

## 주요 메서드

- `getCredential(key)`
- `getCredentialByAccountId(accountId)`
- `confirmCredential(key, revision, accountId)`
- `watchCredentialEvents()`
- `listApplicationCommands()`
- `reportApplicationCommandResult(commandId, status, errorCode)`
- `executeApplicationCommand(event, handler)`
- `syncAgent(credentials, deliveredCredentials, configDigest, syncStatus, syncError)`
- `clone() / close()`

## 문제 해결

HTTP, 네트워크, 인증 및 디코딩 실패는 코드와 HTTP 상태를 포함한 SDK 예외/오류 형식을 사용합니다. 사용 후 스트림과 클라이언트를 닫으세요. 복제 클라이언트의 수명은 독립적입니다. 일시적 실패는 애플리케이션 경계에서 재시도하고 비밀이나 인증 헤더는 기록하지 마세요.

`PAMException`

모든 SDK는 프로토콜 버전 1을, Agent 설정은 스키마 버전 1을 사용합니다. client_upgrade_required(HTTP 426)를 받으면 호환성을 확인하고 업그레이드하세요. 알 수 없는 선택 필드와 알림 이벤트는 허용하지만 지원하지 않는 정책은 적용하거나 확인하면 안 됩니다. 수신 확인은 자동 전송되며 자격 증명 적용을 증명하지 않습니다.

## Linux Agent 연동

Agent 동기화 메서드는 Agent 구현을 위한 것입니다. Agent 신원 또는 source와 설정 ID가 필요하며 KnownRevision으로 캐시 및 전달 버전을 보고합니다. Linux 설치, 파일 전달과 로컬 API는 현재 Python Agent가 제공하며 모든 언어의 애플리케이션에서 사용할 수 있습니다.

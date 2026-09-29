# JumpServer PAM Go SDK

이 SDK는 Python 자격 증명 정책 SDK와 기능을 맞춥니다. 허용된 계정 또는 순환 정책의 자격 증명 조회, 적용 버전 확인, 이벤트 구독, 애플리케이션 명령 처리와 Agent 동기화를 제공합니다. URL, HMAC 서명, Digest, UTC 시간, 요청 ID와 프로토콜 헤더는 자동 생성됩니다.

## 환경 요구 사항

- Go 1.23+ / coder/websocket
- `cmd/demo/main.go`

## 설정 및 실행

소스 SDK를 설치하고 아래 설정을 입력하세요. 애플리케이션 관리에서 계정을 허용하고 정책을 연결한 뒤 접속 자료에서 AK/SK와 조직 ID를 가져옵니다. 자리표시자를 교체하고 인증 자료를 안전하게 보관하세요. 복제본마다 안정적이고 고유한 인스턴스 ID를 사용하며 계정 ID 또는 정책 key 중 하나만 지정합니다.

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

SDK는 현재 이 저장소의 소스로 설치하며 공개 패키지 저장소에는 배포되지 않았습니다. /path/to/jumpserver를 절대 경로로 바꾸세요. Go와 Node.js 설치 명령은 애플리케이션 디렉터리에서 실행하고 Java 의존성은 애플리케이션 pom.xml에 추가하세요. 저장소 예제의 로컬 가져오기는 아래 패키지 가져오기로 바꾸세요.

```bash
go mod edit -replace=github.com/jumpserver/jumpserver/apps/accounts/clients/go=/path/to/jumpserver/apps/accounts/clients/go
go get github.com/jumpserver/jumpserver/apps/accounts/clients/go@v0.0.0
```

```go
import pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
```

## 요청 및 응답

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

## 이벤트 및 자격 증명 적용

최초/재연결 snapshot과 credential.updated를 처리합니다. 아래 전체 예제는 subscription, alternating_rotation 및 애플리케이션 명령을 처리합니다. 실제 연결 검증, 연결 풀 전환과 이전 연결 해제를 적용 함수에 구현하세요. 미구현 함수는 예외를 발생시켜 적용하지 않은 버전의 확인을 막습니다. 스냅샷에서 제거된 계정과 권한 취소 이벤트도 애플리케이션 캐시에 반영해야 합니다.

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
	credential, err := client.GetCredential(ctx, pam.CredentialSelector{Key: event.CredentialKey})
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
			if update.CredentialMode == "subscription" && update.AccountID != "" {
				selector.AccountID = update.AccountID
			} else if update.CredentialMode == "alternating_rotation" && key != "" {
				selector.Key = key
			} else {
				continue
			}
			credential, err := client.GetCredential(ctx, selector)
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

교대 회전에서는 실제 연결을 검증하고 연결 풀을 바꾸며 기존 연결을 해제한 뒤 정확한 key, revision, account_id를 확인하세요. 자격 증명 변경 구독은 확인이 필요 없습니다. 연결 검증에 실패하면 확인하면 안 됩니다.

## 애플리케이션 명령

폴링, 명령 실행 권한 요청과 결과 보고는 SDK 메서드로 수행합니다. 실행 요청이 수락된 경우에만 핸들러가 동작합니다. 전환 명령은 요청 버전과 계정을 검사하고 적용 후 확인하며, 재시작 명령은 재시작과 상태 검사를 마쳐야 합니다. 완료 후에만 성공을 보고하며 실패 보고 오류는 원래 업무 예외를 덮어쓰지 않습니다.

## 주요 메서드

- `GetCredential(ctx, CredentialSelector{Key: ...})`
- `GetCredential(ctx, CredentialSelector{AccountID: ...})`
- `ConfirmCredential(ctx, key, revision, accountID)`
- `WatchCredentialEvents(ctx, handler)`
- `ListApplicationCommands(ctx)`
- `ReportApplicationCommandResult(ctx, commandID, status, errorCode)`
- `ExecuteApplicationCommand(ctx, event, handler)`
- `SyncAgent(ctx, AgentSyncOptions{...})`
- `Clone() / Close()`

## 문제 해결

HTTP, 네트워크, 인증 및 디코딩 실패는 코드와 HTTP 상태를 포함한 SDK 예외/오류 형식을 사용합니다. 사용 후 스트림과 클라이언트를 닫으세요. 복제 클라이언트의 수명은 독립적입니다. 일시적 실패는 애플리케이션 경계에서 재시도하고 비밀이나 인증 헤더는 기록하지 마세요.

`PAMError`

모든 SDK는 프로토콜 버전 1을, Agent 설정은 스키마 버전 1을 사용합니다. client_upgrade_required(HTTP 426)를 받으면 호환성을 확인하고 업그레이드하세요. 알 수 없는 선택 필드와 알림 이벤트는 허용하지만 지원하지 않는 정책은 적용하거나 확인하면 안 됩니다. 수신 확인은 자동 전송되며 자격 증명 적용을 증명하지 않습니다.

## Linux Agent 연동

Agent 동기화 메서드는 Agent 구현을 위한 것입니다. Agent 신원 또는 source와 설정 ID가 필요하며 KnownRevision으로 캐시 및 전달 버전을 보고합니다. Linux 설치, 파일 전달과 로컬 API는 현재 Python Agent가 제공하며 모든 언어의 애플리케이션에서 사용할 수 있습니다.

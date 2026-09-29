# cURL — 사용 가이드

이 디렉터리는 기존 account-secret API 진단용 HTTP 서명 스크립트입니다. 애플리케이션 연동에는 Python, Go, Java 또는 Node.js SDK를 사용하세요.

## 환경 요구 사항

- Bash / cURL / OpenSSL / base64
- `demo.sh`

Bash, cURL, OpenSSL, base64가 필요합니다. ASSET과 ACCOUNT를 바꾸고, 서명할 쿼리의 인코딩이 cURL이 실제 전송하는 값과 일치하는지 확인하세요.

## 설정 및 실행

애플리케이션 관리에서 애플리케이션을 생성하고 대상 자산 계정을 허용하세요. 아래 엔드포인트, 애플리케이션 AK/SK, 조직 ID를 설정하고 실행 전에 모든 자리 표시자를 실제 값으로 바꾸세요.

```bash
cd apps/accounts/clients/curl
export API_URL='https://jumpserver.example.com'
export API_KEY_ID='<app-id>'
export API_KEY_SECRET='<app-secret>'
export ORG_ID='<org-id>'

bash demo.sh
```

기본 자산은 ubuntu_docker, 계정은 root입니다. 예제 코드에서 실제 허용된 이름으로 바꾸세요. 명령은 저장소 루트에서 실행합니다. 예제 출력에는 비밀 정보가 포함되므로 애플리케이션 로그에 기록하지 마세요.

## 요청 및 응답

```http
GET /api/v1/accounts/integration-applications/account-secret/?asset=ubuntu_docker&account=root
```

```json
{"id":"<app-id>","secret":"<account-secret>"}
```

id는 애플리케이션을 식별하며 계정 리비전이 아닙니다. secret이 null이면 서버의 비밀 정보 보기 설정이 제한한 것일 수 있습니다. 이 예제는 자격 증명 이벤트, 적용 리비전 보고, 애플리케이션 명령을 구현하지 않습니다.

## 문제 해결

401은 AK/SK, 조직, 호스트 시간, 서명 URL을 확인하세요. 403은 애플리케이션 상태와 계정 권한, 400은 자산/계정 선택과 URL 인코딩을 확인하세요. 비밀 정보와 Authorization 헤더를 기록하지 마세요. 이름은 허용된 자산과 계정에 일치해야 합니다.

## 자격 증명 정책 연동

아래 서명 정보와 프로토콜 표는 진단 참고 자료입니다. 자격 증명 정책에는 SDK 메서드를 사용하거나 Python Agent의 JSON 파일, EnvironmentFile 또는 Unix Socket을 사용하세요.

| HTTP | API | JSON / query |
| --- | --- | --- |
| GET | `/api/v1/accounts/credential-client/credential/` | `instance_id`, `key` / `account_id` |
| POST | `/api/v1/accounts/credential-client/confirm/` | `instance_id`, `key`, `revision`, `account_id` |
| GET | `/api/v1/accounts/credential-client/commands/` | `instance_id` |
| POST | `/api/v1/accounts/credential-client/command-result/` | `instance_id`, `command_id`, `status`, `error_code` |
| WebSocket | `/ws/accounts/credential-events/` | `instance_id` |

아래 헤더 순서로 HMAC-SHA256 서명을 계산합니다. request-target에는 인코딩된 경로와 쿼리, Digest에는 실제 본문의 SHA-256, X-JMS-Request-ID에는 고유 UUID, Date에는 HTTP UTC 시간을 넣습니다. X-JMS-Client-Version, X-JMS-Protocol-Version: 1, SDK의 X-JMS-Config-Schema-Version: 0을 설정하세요. API와 WebSocket은 애플리케이션 AK/SK와 안정적이고 고유한 instance_id를 사용하며 요청과 재연결마다 서명을 생성합니다.

```text
(request-target) accept date digest x-jms-request-id x-jms-org
x-jms-client-version x-jms-protocol-version x-jms-config-schema-version
```

교대 회전에서는 실제 연결을 검증하고 연결 풀을 바꾸며 기존 연결을 해제한 뒤 정확한 key, revision, account_id를 확인하세요. 자격 증명 변경 구독은 확인이 필요 없습니다. 연결 검증에 실패하면 확인하면 안 됩니다.

received는 이벤트를 읽었다는 뜻입니다. event_id가 있는 업무 이벤트를 처리하기 전에 같은 WebSocket에서 received를 보냅니다. snapshot과 pong에는 수신 확인이 필요 없습니다. 연결과 재연결마다 스냅샷을 동기화하고 credential.updated, 권한 취소, 설정 변경을 처리하세요.

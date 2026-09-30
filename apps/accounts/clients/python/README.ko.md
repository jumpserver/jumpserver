# JumpServer PAM Python SDK / Agent

Python 3.9+는 자격 증명 정책 SDK를 제공합니다. Go jms-pam-agent는 Python 없이 로컬 파일, 고정 작업 또는 Socket으로 자격 증명을 전달합니다. Linux, macOS, Windows에서 포그라운드 실행을 지원하며 내장 systemd 설치는 Linux 전용입니다.

<!-- agent-doc:start -->

## Go Agent 연동

systemd와 애플리케이션 사용자가 있는 Linux를 준비하고 마법사에서 jms_pam_agent.json을 다운로드합니다. Go 바이너리를 빌드하거나 받아 설치하고 안정적인 고유 인스턴스 ID를 사용합니다. 로컬 구성은 /etc/jms-pam-agent/agent.json이며 서비스는 jms-pam-agent로 고정됩니다.

```bash
cd apps/accounts/clients/go
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
chmod 0600 ./jms_pam_agent.json
sudo /usr/local/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

내장 설치에는 Linux와 root가 필요합니다. macOS, 비 root Linux 또는 Windows에서는 접속 마법사에서 JSON 또는 Socket을 선택하고 init-local 및 run --local --config 명령을 실행하세요. 한 번만 초기화하고 생성된 비공개 로컬 설정을 재사용하세요. 포그라운드 모드는 systemd 작업을 수행하지 않습니다.

`/etc/jms-pam-agent/agent.json`: `0600`; `state_file`, `event_file`, `delivery.delivery_root`, `delivery.socket_path`.

- JSON: `/opt/jumpserver-pam/credentials/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<credential-key>.env`
- Unix Socket: `/run/jms-pam-agent/agent.sock`

JSON은 파일 전달, EnvironmentFile은 지정된 systemd 서비스, Unix Socket은 로컬 API를 제공합니다. Agent는 전달 성공 후 전달 리비전을 저장하고 애플리케이션은 검증 및 적용 후 적용 리비전을 저장합니다. Socket은 앱 사용자 소유이며 권한은 0600입니다. 해당 사용자로 요청하세요.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<credential-key>.env
```

systemd unit은 EnvironmentFile을 참조해야 합니다. 앱이 파일을 다시 읽을 때만 reload를 사용하세요. reload는 실행 중인 프로세스에 새 환경 변수를 주입하지 않습니다. 경로, 사용자, 서비스, 작업 권한은 설치 시 고정되며 확장하려면 다시 설치해야 합니다.

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


### 로컬 API 및 확인

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

교대 회전에서는 실제 연결을 검증하고 연결 풀을 바꾸며 기존 연결을 해제한 뒤 정확한 key, revision, account_id를 확인하세요. 자격 증명 변경 구독은 확인이 필요 없습니다. 연결 검증에 실패하면 확인하면 안 됩니다.

```bash
/usr/local/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jms-pam-agent/agent.sock'
```

교대 회전만 confirm을 사용합니다. 로컬 확인은 먼저 영구 저장합니다. confirmed는 Core가 수락한 상태, pending은 나중에 재시도할 상태입니다. 파일 저장이나 서비스 재시작만으로 확인하지 마세요.

### 문제 해결

```bash
sudo systemctl start jms-pam-agent
sudo systemctl status jms-pam-agent --no-pager
sudo journalctl -u jms-pam-agent -n 100 --no-pager
sudo systemctl restart jms-pam-agent
```

Agent는 시작 시, 관련 이벤트 수신 시, 300초마다 동기화합니다. 네트워크 오류는 이미 가져온 최신 승인 자격 증명을 유지합니다. 신원이나 권한 거부 시 Socket 조회를 차단하고 서명된 동기화가 성공하면 복구합니다. 전달된 파일은 유지됩니다. SIGINT/SIGTERM은 서비스, 연결, 읽기 스레드를 종료합니다.

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Python SDK 연동

정책을 생성하여 앱에 바인딩하고 자산 계정을 허용한 뒤 연동 마법사에서 jms_pam_config.py를 다운로드하세요. Python 3.9+가 필요합니다. 아래 저장소 설치 명령 또는 다운로드한 SDK 디렉터리에서 python3 -m pip install .을 실행하세요.

```bash
python3 -m pip install ./apps/accounts/clients/python
```

jms_pam_config.py를 앱이 읽을 수 있는 위치에 두세요. client_options에는 신원 정보가 있으므로 커밋하거나 로그에 쓰지 마세요. 복제본마다 안정적이고 고유한 instance_id를 사용하세요. get_credential에는 account_id 또는 회전 정책의 key 중 하나만 지정하세요.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


with Client(instance_id=instance_id, **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### 이벤트 및 자격 증명 적용

초기/재연결 snapshot과 credential.updated를 처리하세요. 예제는 subscription과 alternating_rotation을 구분합니다. apply_credential에서 실제 연결을 검증하고 연결 풀을 바꾸며 기존 연결을 해제하세요. 미구현 함수는 예외를 발생시켜 적용되지 않은 자격 증명의 확인을 막습니다.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def apply_credential(credential):
    raise NotImplementedError('애플리케이션 자격 증명 전환을 구현하고 검증하세요')


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

교대 회전에서는 실제 연결을 검증하고 연결 풀을 바꾸며 기존 연결을 해제한 뒤 정확한 key, revision, account_id를 확인하세요. 자격 증명 변경 구독은 확인이 필요 없습니다. 연결 검증에 실패하면 확인하면 안 됩니다.

SDK는 비즈니스 이벤트를 반환하기 전에 received 수신 확인을 가능한 범위에서 자동 전송합니다. 애플리케이션은 추가로 전송할 필요가 없습니다. 수신 확인은 이벤트를 읽었다는 뜻이며 자격 증명 적용이나 적용 확인을 대신하지 않습니다. 최초 및 재연결 스냅샷을 처리하세요. snapshot과 pong에는 수신 확인이 필요하지 않습니다.

## 이벤트 처리기

로컬 상태를 초기화한 뒤 감시를 시작합니다. Python과 Node.js는 서브클래스, Go는 EventHandlers, Java는 CredentialEventListener를 사용합니다. 예제의 실제 연결 전환을 구현해야 합니다. 기존 API도 유지됩니다.

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

초기 및 재연결 snapshot과 credential.updated는 모드별로 자격 증명을 조회하고 처리기를 순차 호출합니다. 읽기와 업무 처리는 최대 128개 큐를 사용하며 가득 차면 역압력이 발생합니다. 조회 또는 적용 실패는 1–30초 지수 백오프로 재시도하며 매번 다시 조회합니다. 같은 대상의 새 이벤트는 재시도를 대체하고, snapshot은 범위를 재설정하며 취소와 구성 변경은 재시도를 제거합니다. 처리는 반복 가능해야 합니다. 관찰 및 취소 훅은 자동 재시도하지 않으며 명령은 실행 권한을 먼저 요청해야 합니다. received는 수신만 의미하며 SDK는 회전을 자동 확인하지 않습니다.이전 버전의 이벤트는 최신 버전 조회의 대기 중인 재시도를 취소하지 않습니다.

`watch_events(stop_event=...)` / `start_events(stop_event=...)`; `stop_events()` / `close()`

watch_events는 중지까지 기다립니다. start_events는 초기 동기화 완료를 보장하지 않으므로 준비 상태를 기다리세요. 클라이언트당 감시 하나만 허용됩니다. stop_events와 close는 처리 종료를 기다립니다. 훅 안에서도 중지할 수 있습니다. clone은 서브클래스 상태를 초기화합니다.

### 최신 자격 증명과 백엔드 장애

먼저 API를 요청합니다. 성공하면 보유한 최신 값을 교체하며 오래된 버전으로 새 값을 덮어쓰지 않고 시간 만료도 없습니다. 시간 초과, 네트워크 오류 또는 HTTP 5xx일 때만 같은 선택자의 마지막 성공 값을 로컬 표시와 함께 반환합니다. 이전 값이 없으면 원래 오류입니다. SDK는 업데이트, 취소 또는 종료까지 클라이언트 메모리에 보유하며 clone과 재시작은 빈 상태로 시작합니다. Agent는 기존의 보호된 로컬 상태에 저장합니다. HTTP 401/403/404 또는 client_upgrade_required는 SDK 값을 삭제하고 실패하며 잘못된 성공 응답도 실패합니다. 취소는 해당 값을, snapshot은 권한 범위 밖 값을 삭제합니다. 구성 변경은 다음 snapshot으로 범위를 확인할 때까지 보유합니다.Agent는 HTTP 동기화 전에 명시적 취소와 snapshot 범위 축소를 적용하고 저장하며, 백엔드 장애 중이나 재시작 후에도 해당 로컬 조회를 차단합니다.credential_not_found(HTTP 400) 응답도 SDK 보관 값을 삭제합니다. account_id로 직접 pull하려면 항상 실시간 API 응답이 필요합니다. push 스냅샷은 캐시된 pull 권한을 증명하지 않습니다.

- `credential.from_local`
- `get_credential(key=..., allow_local_fallback=False)` / `get_credential(account_id=..., allow_local_fallback=False)`

관리된 감시를 켜면 snapshot과 credential.updated가 자동 조회하고 보유 값을 교체한 뒤 업무 훅을 호출합니다. 실패하면 이전 값을 유지하고 재시도합니다. Agent도 업데이트 알림으로 조회하며 장애 시 이전 값을 유지합니다. 업데이트와 수동 전환에는 아래 API 조회 필수 호출을 사용하세요. 보유 값은 새로 조회한 버전이 아니며 회전을 자동 확인하지 않습니다.

유휴 시 10초마다 ping을 보내고 약 30초간 메시지가 없으면 재연결합니다. 1–30초 지수 백오프와 새 서명을 사용합니다. snapshot은 현재 상태를 복원하며 과거 이벤트를 재생하지 않습니다.



### 애플리케이션 명령

list_application_commands로 대기 요청을 조회하고 execute_application_command(event, handler)로 실행을 신청하세요. accepted가 true일 때만 처리합니다. 전환 처리는 요청한 계정/리비전을 확인하고 적용 및 확인하며 재시작 처리는 재시작과 상태 검증 후 성공을 보고합니다. 실패 보고 오류는 원래 처리 예외를 가리지 않습니다.

### 주요 메서드

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `watch_events(stop_event=...)` / `start_events(stop_event=...)` / `stop_events()`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

with 또는 close로 HTTP 세션과 이벤트 스트림을 닫고 clone으로 독립 세션을 만듭니다. HTTP, 네트워크, 인증, 해석 오류는 code, status_code, detail, original_error가 있는 PAMError로 반환됩니다. 일시 오류를 재시도하고 권한 거부를 명확하게 처리하며 자격 증명을 기록하지 마세요.

새 코드는 snake_case 키워드 메서드와 dataclass 속성을 사용합니다. 기존 credential.v1 요청 객체 API는 DeprecationWarning과 함께 유지됩니다. SDK와 Agent는 버전 1 프로토콜을 공유하고 sync_agent는 보관/전달 리비전을 KnownRevision으로 받습니다.

<!-- sdk-doc:end -->

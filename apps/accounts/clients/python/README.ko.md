# JumpServer PAM Python SDK / Agent

Python 3.9+에서 자격 증명 정책 SDK와 Linux Agent를 사용할 수 있습니다. SDK는 애플리케이션 AK/SK를 사용하고 Agent는 다른 언어의 애플리케이션에도 로컬로 자격 증명을 전달합니다.

<!-- agent-doc:start -->

## Linux Agent 연동

systemd, Python 3.9+, 애플리케이션 사용자가 있는 Linux 호스트를 준비하세요. 정책에 애플리케이션을 바인딩하고 계정을 허용하세요. 교대 회전에는 두 계정의 권한이 필요합니다. 연동 마법사에서 Agent, 실행 사용자, 설치 경로, 전달 방식을 선택하고 jms_pam_agent.json을 다운로드하세요. SDK를 설치하고 아래 기본 경로 명령을 실행합니다. 각 복제본에 안정적이고 고유한 인스턴스 ID를 지정하세요.

```bash
sudo python3 -m venv /opt/jumpserver-pam/venv
sudo /opt/jumpserver-pam/venv/bin/python -m pip install '<sdk-directory>'
sudo /opt/jumpserver-pam/venv/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

아래는 기본 경로입니다. configuration-id는 부트스트랩, credential-key는 정책에서 확인하세요. 실제 설치 경로를 사용하세요. 부트스트랩에는 AK/SK가 포함됩니다. 읽기 권한을 제한하고 설치 후 다운로드 파일을 삭제하며 설치된 설정을 보호하세요.

- JSON: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env`
- Unix Socket: `/run/jumpserver-pam/<configuration-id>/agent.sock`

JSON은 파일 전달, EnvironmentFile은 지정된 systemd 서비스, Unix Socket은 로컬 API를 제공합니다. Agent는 전달 성공 후 전달 리비전을 저장하고 애플리케이션은 검증 및 적용 후 적용 리비전을 저장합니다. Socket은 앱 사용자 소유이며 권한은 0600입니다. 해당 사용자로 요청하세요.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env
```

systemd unit은 EnvironmentFile을 참조해야 합니다. 앱이 파일을 다시 읽을 때만 reload를 사용하세요. reload는 실행 중인 프로세스에 새 환경 변수를 주입하지 않습니다. 경로, 사용자, 서비스, 작업 권한은 설치 시 고정되며 확장하려면 다시 설치해야 합니다.

### 로컬 API 및 확인

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

교대 회전에서는 실제 연결을 검증하고 연결 풀을 바꾸며 기존 연결을 해제한 뒤 정확한 key, revision, account_id를 확인하세요. 자격 증명 변경 구독은 확인이 필요 없습니다. 연결 검증에 실패하면 확인하면 안 됩니다.

```bash
/opt/jumpserver-pam/venv/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jumpserver-pam/<configuration-id>/agent.sock'
```

교대 회전만 confirm을 사용합니다. 로컬 확인은 먼저 영구 저장합니다. confirmed는 Core가 수락한 상태, pending은 나중에 재시도할 상태입니다. 파일 저장이나 서비스 재시작만으로 확인하지 마세요.

### 문제 해결

```bash
sudo systemctl status 'jms-pam-agent-<configuration-id>.service' --no-pager
sudo journalctl -u 'jms-pam-agent-<configuration-id>.service' -n 100 --no-pager
sudo systemctl restart 'jms-pam-agent-<configuration-id>.service'
```

Agent는 시작 시, 관련 이벤트 수신 시, 300초마다 동기화합니다. 네트워크 오류는 허용된 캐시를 유지합니다. 신원이나 권한 거부 시 Socket 조회를 차단하고 서명된 동기화가 성공하면 복구합니다. 전달된 파일은 유지됩니다. SIGINT/SIGTERM은 서비스, 연결, 읽기 스레드를 종료합니다.

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
from jms_pam_config import client_options


with Client(instance_id="app-node-1", **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### 이벤트 및 자격 증명 적용

초기/재연결 snapshot과 credential.updated를 처리하세요. 예제는 subscription과 alternating_rotation을 구분합니다. apply_credential에서 실제 연결을 검증하고 연결 풀을 바꾸며 기존 연결을 해제하세요. 미구현 함수는 예외를 발생시켜 적용되지 않은 자격 증명의 확인을 막습니다.

```python
from jms_pam import Client
from jms_pam_config import client_options


def apply_credential(credential):
    raise NotImplementedError('애플리케이션 자격 증명 전환을 구현하고 검증하세요')


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

교대 회전에서는 실제 연결을 검증하고 연결 풀을 바꾸며 기존 연결을 해제한 뒤 정확한 key, revision, account_id를 확인하세요. 자격 증명 변경 구독은 확인이 필요 없습니다. 연결 검증에 실패하면 확인하면 안 됩니다.

SDK는 비즈니스 이벤트를 반환하기 전에 received 수신 확인을 가능한 범위에서 자동 전송합니다. 애플리케이션은 추가로 전송할 필요가 없습니다. 수신 확인은 이벤트를 읽었다는 뜻이며 자격 증명 적용이나 적용 확인을 대신하지 않습니다. 최초 및 재연결 스냅샷을 처리하세요. snapshot과 pong에는 수신 확인이 필요하지 않습니다.

### 애플리케이션 명령

list_application_commands로 대기 요청을 조회하고 execute_application_command(event, handler)로 실행을 신청하세요. accepted가 true일 때만 처리합니다. 전환 처리는 요청한 계정/리비전을 확인하고 적용 및 확인하며 재시작 처리는 재시작과 상태 검증 후 성공을 보고합니다. 실패 보고 오류는 원래 처리 예외를 가리지 않습니다.

### 주요 메서드

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

with 또는 close로 HTTP 세션과 이벤트 스트림을 닫고 clone으로 독립 세션을 만듭니다. HTTP, 네트워크, 인증, 해석 오류는 code, status_code, detail, original_error가 있는 PAMError로 반환됩니다. 일시 오류를 재시도하고 권한 거부를 명확하게 처리하며 자격 증명을 기록하지 마세요.

새 코드는 snake_case 키워드 메서드와 dataclass 속성을 사용합니다. 기존 credential.v1 요청 객체 API는 DeprecationWarning과 함께 유지됩니다. SDK와 Agent는 버전 1 프로토콜을 공유하고 sync_agent는 캐시/전달 리비전을 KnownRevision으로 받습니다.

<!-- sdk-doc:end -->

# JumpServer PAM Node.js SDK

이 SDK는 Python 자격 증명 정책 SDK와 기능을 맞춥니다. 허용된 계정 또는 순환 정책의 자격 증명 조회, 적용 버전 확인, 이벤트 구독, 애플리케이션 명령 처리와 Agent 동기화를 제공합니다. URL, HMAC 서명, Digest, UTC 시간, 요청 ID와 프로토콜 헤더는 자동 생성됩니다.

## 환경 요구 사항

- Node.js 20.3+ / ws
- `demo.js`

## 설정 및 실행

소스 SDK를 설치하고 아래 설정을 입력하세요. 애플리케이션 관리에서 pull 대상 계정을 허용하고, push 또는 순환이 필요한 경우에만 정책을 연결합니다. 접속 자료에서 AK/SK와 조직 ID를 가져옵니다. 자리표시자를 교체하고 인증 자료를 안전하게 보관하세요. 복제본마다 안정적이고 고유한 인스턴스 ID를 사용하며 계정 ID 또는 정책 key 중 하나만 지정합니다.

```bash
cd apps/accounts/clients/node
export JMS_ENDPOINT='https://jumpserver.example.com'
export JMS_APP_ID='<app-id>'
export JMS_APP_SECRET='<app-secret>'
export JMS_ORG_ID='<org-id>'
export JMS_INSTANCE_ID='app-node-1'
export JMS_ACCOUNT_ID='<account-id>'

npm ci
node demo.js
```

SDK는 현재 이 저장소의 소스로 설치하며 공개 패키지 저장소에는 배포되지 않았습니다. /path/to/jumpserver를 절대 경로로 바꾸세요. Go와 Node.js 설치 명령은 애플리케이션 디렉터리에서 실행하고 Java 의존성은 애플리케이션 pom.xml에 추가하세요. 저장소 예제의 로컬 가져오기는 아래 패키지 가져오기로 바꾸세요.

```bash
npm install /path/to/jumpserver/apps/accounts/clients/node
```

```javascript
const { Client } = require('@jumpserver/pam')
// ESM: import { Client } from '@jumpserver/pam'
```

## 요청 및 응답

```javascript
'use strict'

const { Client } = require('./index')

async function main() {
  const client = new Client({
    endpoint: process.env.JMS_ENDPOINT,
    appId: process.env.JMS_APP_ID,
    appSecret: process.env.JMS_APP_SECRET,
    instanceId: process.env.JMS_INSTANCE_ID,
    orgId: process.env.JMS_ORG_ID,
  })
  try {
    const credential = await client.getCredential({ accountId: process.env.JMS_ACCOUNT_ID })
    // Pass credential.account.username / secret to the application connection pool.
    console.log(
      `Fetched revision ${credential.revision}; implement application credential switching.`,
    )
  } finally {
    client.close()
  }
}

if (require.main === module)
  main().catch((error) => {
    console.error(error.code || error.name)
    process.exitCode = 1
  })
```

## 이벤트 처리기

로컬 상태를 초기화한 뒤 감시를 시작합니다. Python과 Node.js는 서브클래스, Go는 EventHandlers, Java는 CredentialEventListener를 사용합니다. 예제의 실제 연결 전환을 구현해야 합니다. 기존 API도 유지됩니다.

```javascript
'use strict'
const { Client } = require('./index')

class MyClient extends Client {
  constructor(options) {
    super(options)
    this.credentials = new Map()
    this.modes = new Map()
  }
  async onEvent(event) {
    if (event.event === 'snapshot') {
      this.modes.clear()
      for (const update of event.credentials || [])
        this.modes.set(update.credentialKey || update.key, update.credentialMode)
      for (const key of this.credentials.keys())
        if (!this.modes.has(key)) this.credentials.delete(key) // Also release connections.
    } else if (event.event === 'credential.updated') {
      this.modes.set(event.credentialKey || event.key, event.credentialMode)
    }
    // Use executeApplicationCommand for command events; see events.js.
  }
  async onCredentialChanged(credential, { signal }) {
    await this.applyCredential(credential, { signal })
    if (this.modes.get(credential.key) === 'alternating_rotation')
      await this.confirmCredential({ key: credential.key, revision: credential.revision,
        accountId: credential.account.id, signal })
    this.credentials.set(credential.key, credential)
  }
  async applyCredential(credential, { signal }) {
    throw new Error('Implement connection validation, pool switching and old connection cleanup')
  }
  async onCredentialRevoked(event) {
    this.credentials.delete(event.credentialKey || event.key) // Also release affected connections.
  }
}

async function main() {
  const client = new MyClient({ endpoint: process.env.JMS_ENDPOINT, appId: process.env.JMS_APP_ID,
    appSecret: process.env.JMS_APP_SECRET, instanceId: process.env.JMS_INSTANCE_ID, orgId: process.env.JMS_ORG_ID })
  const stop = () => client.close()
  process.once('SIGINT', stop); process.once('SIGTERM', stop)
  try { await client.watchEvents() }
  finally {
    client.close(); await client.stopEvents()
    process.removeListener('SIGINT', stop); process.removeListener('SIGTERM', stop)
  }
}
if (require.main === module) main().catch((error) => {
  console.error(error.code || error.name); process.exitCode = 1
})
module.exports = { MyClient }
```

초기 및 재연결 snapshot과 credential.updated는 모드별로 자격 증명을 조회하고 처리기를 순차 호출합니다. 읽기와 업무 처리는 최대 128개 큐를 사용하며 가득 차면 역압력이 발생합니다. 조회 또는 적용 실패는 1–30초 지수 백오프로 재시도하며 매번 다시 조회합니다. 같은 대상의 새 이벤트는 재시도를 대체하고, snapshot은 범위를 재설정하며 취소와 구성 변경은 재시도를 제거합니다. 처리는 반복 가능해야 합니다. 관찰 및 취소 훅은 자동 재시도하지 않으며 명령은 실행 권한을 먼저 요청해야 합니다. received는 수신만 의미하며 SDK는 회전을 자동 확인하지 않습니다.이전 버전의 이벤트는 최신 버전 조회의 대기 중인 재시도를 취소하지 않습니다.

`watchEvents({signal})` / `startEvents({signal})`; `stopEvents()` / `await subscription.stop()` / `await subscription.done`

watchEvents는 이벤트 루프를 막지 않습니다. startEvents는 동기화 완료를 보장하지 않습니다. 감시는 하나만 허용됩니다. async 훅은 순차 await되며 AbortSignal을 받습니다. close 뒤 외부에서 stop() 또는 done을 기다리세요. 자신의 done은 기다리지 마세요. clone은 기본 Client를 반환합니다.

### 최신 자격 증명과 백엔드 장애

먼저 API를 요청합니다. 성공하면 보유한 최신 값을 교체하며 오래된 버전으로 새 값을 덮어쓰지 않고 시간 만료도 없습니다. 시간 초과, 네트워크 오류 또는 HTTP 5xx일 때만 같은 선택자의 마지막 성공 값을 로컬 표시와 함께 반환합니다. 이전 값이 없으면 원래 오류입니다. SDK는 업데이트, 취소 또는 종료까지 클라이언트 메모리에 보유하며 clone과 재시작은 빈 상태로 시작합니다. Agent는 기존의 보호된 로컬 상태에 저장합니다. HTTP 401/403/404 또는 client_upgrade_required는 SDK 값을 삭제하고 실패하며 잘못된 성공 응답도 실패합니다. 취소는 해당 값을, snapshot은 권한 범위 밖 값을 삭제합니다. 구성 변경은 다음 snapshot으로 범위를 확인할 때까지 보유합니다.Agent는 HTTP 동기화 전에 명시적 취소와 snapshot 범위 축소를 적용하고 저장하며, 백엔드 장애 중이나 재시작 후에도 해당 로컬 조회를 차단합니다.credential_not_found(HTTP 400) 응답도 SDK 보관 값을 삭제합니다. account_id로 직접 pull하려면 항상 실시간 API 응답이 필요합니다. push 스냅샷은 캐시된 pull 권한을 증명하지 않습니다.

- `credential.fromLocal`
- `getCredential({key, allowLocalFallback: false})` / `getCredential({accountId, allowLocalFallback: false})`

관리된 감시를 켜면 snapshot과 credential.updated가 자동 조회하고 보유 값을 교체한 뒤 업무 훅을 호출합니다. 실패하면 이전 값을 유지하고 재시도합니다. Agent도 업데이트 알림으로 조회하며 장애 시 이전 값을 유지합니다. 업데이트와 수동 전환에는 아래 API 조회 필수 호출을 사용하세요. 보유 값은 새로 조회한 버전이 아니며 회전을 자동 확인하지 않습니다.

유휴 시 10초마다 ping을 보내고 약 30초간 메시지가 없으면 재연결합니다. 1–30초 지수 백오프와 새 서명을 사용합니다. snapshot은 현재 상태를 복원하며 과거 이벤트를 재생하지 않습니다.



## 이벤트 및 자격 증명 적용

최초/재연결 snapshot과 credential.updated를 처리합니다. 아래 전체 예제는 subscription, alternating_rotation 및 애플리케이션 명령을 처리합니다. 실제 연결 검증, 연결 풀 전환과 이전 연결 해제를 적용 함수에 구현하세요. 미구현 함수는 예외를 발생시켜 적용하지 않은 버전의 확인을 막습니다. 스냅샷에서 제거된 계정과 권한 취소 이벤트도 애플리케이션 상태에 반영해야 합니다.

```javascript
'use strict'
const { Client } = require('./index')

async function applyCredential(credential) {
  // Validate a real connection, switch the pool, then release old connections.
  throw new Error('Implement application credential switching')
}
async function restartApplication() {
  throw new Error('Implement application restart and health check')
}
async function handleCommand(client, event) {
  if (event.event === 'application.restart.requested') return restartApplication()
  if (event.event !== 'credential.switch.requested')
    throw new Error('Unsupported application command')
  const credential = await client.getCredential({ key: event.credentialKey, allowLocalFallback: false })
  if (credential.revision !== event.revision || credential.account.id !== event.accountId)
    throw new Error('Requested account version is superseded')
  await applyCredential(credential)
  await client.confirmCredential({
    key: credential.key,
    revision: credential.revision,
    accountId: credential.account.id,
  })
}
async function main() {
  const client = new Client({
    endpoint: process.env.JMS_ENDPOINT,
    appId: process.env.JMS_APP_ID,
    appSecret: process.env.JMS_APP_SECRET,
    instanceId: process.env.JMS_INSTANCE_ID,
    orgId: process.env.JMS_ORG_ID,
  })
  const stop = () => client.close()
  process.once('SIGINT', stop)
  process.once('SIGTERM', stop)
  try {
    for await (const event of client.watchCredentialEvents()) {
      if (event.commandId) {
        try {
          await client.executeApplicationCommand(event, (command) => handleCommand(client, command))
        } catch {
          /* Failure is reported; keep secrets out of logs. */
        }
        continue
      }
      const updates =
        event.event === 'snapshot'
          ? event.credentials
          : event.event === 'credential.updated'
            ? [event]
            : []
      // On snapshots, remove application caches absent from the new authorized scope.
      for (const update of updates || []) {
        const mode = update.credentialMode
        const key = update.credentialKey || update.key
        let credential
        if (mode === 'subscription' && update.accountId && key) {
          const subscriptionKey = key.endsWith(`:${update.accountId}`) ? key : `${key}:${update.accountId}`
          credential = await client.getCredential({ key: subscriptionKey, allowLocalFallback: false })
        }
        else if (mode === 'alternating_rotation' && key)
          credential = await client.getCredential({ key, allowLocalFallback: false })
        else continue
        await applyCredential(credential)
        if (mode === 'alternating_rotation')
          await client.confirmCredential({
            key: credential.key,
            revision: credential.revision,
            accountId: credential.account.id,
          })
      }
    }
  } finally {
    client.close()
    process.removeListener('SIGINT', stop)
    process.removeListener('SIGTERM', stop)
  }
}
if (require.main === module)
  main().catch((error) => {
    console.error(error.code || error.name)
    process.exitCode = 1
  })
```

교대 회전에서는 실제 연결을 검증하고 연결 풀을 바꾸며 기존 연결을 해제한 뒤 정확한 key, revision, account_id를 확인하세요. 자격 증명 변경 구독은 확인이 필요 없습니다. 연결 검증에 실패하면 확인하면 안 됩니다.

## 애플리케이션 명령

폴링, 명령 실행 권한 요청과 결과 보고는 SDK 메서드로 수행합니다. 실행 요청이 수락된 경우에만 핸들러가 동작합니다. 전환 명령은 요청 버전과 계정을 검사하고 적용 후 확인하며, 재시작 명령은 재시작과 상태 검사를 마쳐야 합니다. 완료 후에만 성공을 보고하며 실패 보고 오류는 원래 업무 예외를 덮어쓰지 않습니다.

## 주요 메서드

- `getCredential({key})`
- `getCredential({accountId})`
- `getCredential({key, allowLocalFallback: false})`
- `confirmCredential({key, revision, accountId})`
- `watchCredentialEvents({signal})`
- `watchEvents({signal}) / startEvents({signal}) / stopEvents()`
- `EventSubscription.stop() / done`
- `listApplicationCommands()`
- `reportApplicationCommandResult({commandId, status, errorCode})`
- `executeApplicationCommand(event, handler)`
- `syncAgent({credentials, deliveredCredentials, ...})`
- `clone() / close()`

## 문제 해결

HTTP, 네트워크, 인증 및 디코딩 실패는 코드와 HTTP 상태를 포함한 SDK 예외/오류 형식을 사용합니다. 사용 후 스트림과 클라이언트를 닫으세요. 복제 클라이언트의 수명은 독립적입니다. 일시적 실패는 애플리케이션 경계에서 재시도하고 비밀이나 인증 헤더는 기록하지 마세요.

`PAMError`

모든 SDK는 프로토콜 버전 1을, Agent 설정은 스키마 버전 1을 사용합니다. client_upgrade_required(HTTP 426)를 받으면 호환성을 확인하고 업그레이드하세요. 알 수 없는 선택 필드와 알림 이벤트는 허용하지만 지원하지 않는 정책은 적용하거나 확인하면 안 됩니다. 수신 확인은 자동 전송되며 자격 증명 적용을 증명하지 않습니다.

## Go Agent 연동

인증에는 app_id, app_secret, org_id 및 안정적인 instance_id를 사용하며 권한은 애플리케이션에 연결된 정책을 따릅니다. 경로와 서비스 동작은 모두 로컬 설정입니다. state_file은 최신 암호를 유지하고 event_file은 비밀 없는 이벤트 정보를 추가합니다. delivery는 기본 출력을, rules는 파일, 템플릿 및 reload/restart 또는 고정 스크립트를 지정합니다. 업데이트 알림을 받으면 최신 암호를 가져와 저장하고 파일을 원자적으로 교체한 뒤 동작을 실행합니다. 실패는 재시도합니다. rules에는 get_accounts의 credentials[].key를 사용합니다. 구독 key에는 계정 ID가 포함됩니다. rules가 비어 있으면 key별 기본 파일을 씁니다.

로컬 rules에 파일, JSON/EnvironmentFile 또는 신뢰할 수 있는 템플릿과 systemd reload/restart 또는 고정 실행 파일을 설정합니다. 스크립트는 표준 입력으로 자격 증명 JSON을 받고 고정 인수와 제한 시간을 사용하며 적용을 검증한 후 성공합니다. Core는 실행 경로나 권한을 확장할 수 없습니다. 구성을 수정한 후 Agent를 재시작합니다.

다운로드한 설정에는 Agent 인증 정보와 전달 설정이 포함됩니다. rules에 업무에서 사용하는 계정 ID, 설정 갱신, 적용 동작, 실행 중인 연결 확인을 지정합니다. allow_account_switch를 설정하면 동일한 규칙으로 A/B 양방향 교체를 처리합니다. 선택적 credential_check는 파일 변경 전에 새 로그인을 검증합니다. 상태, 이벤트, Socket 경로와 300초 조정 간격에는 기본값이 있습니다. rules가 비어 있으면 자격 증명별 기본 파일을 기록합니다.

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

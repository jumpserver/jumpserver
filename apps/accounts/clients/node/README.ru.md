# JumpServer PAM Node.js SDK

SDK соответствует функциям Python SDK политик учётных данных: получение по разрешённому аккаунту или политике ротации, подтверждение применённых версий, события, команды и синхронизация Agent. URL, HMAC-подпись, Digest, дата UTC, ID запроса и заголовки формируются автоматически.

## Требования

- Node.js 20.3+ / ws
- `demo.js`

## Настройка и запуск

Установите исходный SDK и задайте параметры ниже. Разрешите аккаунты для pull в управлении приложениями; привязывайте политики только при необходимости push или ротации. Получите AK/SK и ID организации из материалов подключения. Замените шаблонные значения и защитите секреты развёртывания. Каждой реплике нужен стабильный уникальный ID. Укажите только один селектор: ID аккаунта или key политики.

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

SDK устанавливаются из исходного кода этого репозитория и ещё не опубликованы в общедоступных реестрах пакетов. Замените /path/to/jumpserver абсолютным путём. Команды установки Go и Node.js выполняйте в каталоге приложения; зависимость Java добавьте в pom.xml приложения. Локальные импорты из примеров замените импортами пакетов ниже.

```bash
npm install /path/to/jumpserver/apps/accounts/clients/node
```

```javascript
const { Client } = require('@jumpserver/pam')
// ESM: import { Client } from '@jumpserver/pam'
```

## Запрос и ответ

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

## Обработчики событий

Инициализируйте локальное состояние перед запуском подписки. Python и Node.js используют подкласс, Go — EventHandlers, Java — CredentialEventListener. Реализуйте переключение соединений в примере. Прежний API сохранён.

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

Начальный snapshot, snapshot после переподключения и credential.updated получают данные по режиму политики и последовательно вызывают обработчик. Чтение использует очередь на 128 событий; заполнение создаёт обратное давление. Ошибки получения и применения повторяются с экспоненциальной задержкой 1–30 секунд и новым запросом. Новое событие заменяет повтор для той же цели; snapshot обновляет область, отзыв и изменение конфигурации отменяют повторы. Обработчики должны быть идемпотентными. Наблюдатели и отзыв автоматически не повторяются; команды требуют захвата выполнения. received означает чтение; SDK не подтверждает ротацию автоматически. События старых ревизий не отменяют ожидающее получение более новой ревизии.

`watchEvents({signal})` / `startEvents({signal})`; `stopEvents()` / `await subscription.stop()` / `await subscription.done`

watchEvents не блокирует цикл событий; startEvents не гарантирует синхронизацию. Один слушатель на клиент. async-методы ожидаются последовательно и получают AbortSignal. close отменяет работу; ожидайте stop() или done извне. Не ждите собственного done. clone возвращает Client.

### Последние учётные данные и недоступность сервера

Сначала выполняется запрос API. Успешный ответ заменяет сохранённые последние данные; старая версия не заменяет новую, срок истечения по времени отсутствует. Только тайм-аут, сетевой сбой или HTTP 5xx позволяют вернуть последний успешный результат того же селектора с признаком локального источника. Без прежнего значения возвращается исходная ошибка. SDK хранит данные в памяти клиента до обновления, отзыва или закрытия; clone и перезапуск начинают с пустого состояния. Agent использует защищённое локальное состояние. HTTP 401/403/404 или client_upgrade_required очищают данные SDK и вызывают ошибку; некорректный успешный ответ также ошибочен. Отзыв удаляет соответствующие данные, snapshot — данные вне разрешений. Изменение конфигурации сохраняет значения до проверки следующего snapshot. Agent применяет явный отзыв и сокращение области snapshot до HTTP-синхронизации, сохраняет эту область и блокирует соответствующую локальную выдачу даже при сбое сервера или после перезапуска. Ответ credential_not_found (HTTP 400) также удаляет сохранённые значения SDK. Прямой pull по account_id всегда требует ответа API; снимок push не подтверждает право на кешированное значение pull.

- `credential.fromLocal`
- `getCredential({key, allowLocalFallback: false})` / `getCredential({accountId, allowLocalFallback: false})`

При управляемой подписке snapshot и credential.updated автоматически получают данные, заменяют локальное значение и вызывают обработчик. Ошибка обновления сохраняет прежнее значение и запускает повтор. Agent также получает данные по уведомлениям и сохраняет их при сбоях сервера. Для обновления и ручного переключения используйте вызовы с обязательным запросом API ниже. Сохранённое значение не считается новой полученной версией и не подтверждает ротацию автоматически.

При простое ping отправляется каждые 10 секунд. Около 30 секунд без сообщений вызывают переподключение с задержкой 1–30 секунд и новой подписью. snapshot восстанавливает текущее состояние без воспроизведения истории.



## События и применение учётных данных

Обрабатывайте начальный snapshot, снимки переподключения и credential.updated. Полный пример поддерживает subscription, alternating_rotation и команды. Реализуйте проверку реального подключения, переключение пула и освобождение прежних соединений. Заглушка вызывает исключение и запрещает подтверждение до применения. Удаляйте из состояния приложения отсутствующие в снимках аккаунты и обрабатывайте отзыв доступа.

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

При чередующейся ротации проверьте реальное подключение, переключите пул и освободите старые соединения, затем подтвердите точные key, revision и account_id. Подписка на изменение учётных данных подтверждения не требует. При ошибке проверки соединения подтверждать нельзя.

## Команды приложения

Опрос, получение права выполнения и отчёт о результате используют методы SDK. Обработчик выполняется только после принятия заявки. Переключение проверяет версию и аккаунт, применяет и подтверждает; перезапуск проверяет работоспособность после запуска. Сообщайте об успехе после завершения. Ошибка отчёта сохраняет исходное исключение обработчика.

## Основные методы

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

## Устранение неполадок

Ошибки HTTP, сети, аутентификации и декодирования представлены типом ошибки SDK с кодом и HTTP-статусом. Закрывайте потоки и клиенты после использования; жизненные циклы копий независимы. Повторяйте временные сбои на уровне приложения и не записывайте секреты или заголовки авторизации.

`PAMError`

Все SDK используют протокол версии 1; конфигурация Agent — схему версии 1. Ответ client_upgrade_required (HTTP 426) требует проверки совместимости и обновления. Неизвестные необязательные поля и уведомления допустимы; неподдерживаемые политики нельзя применять или подтверждать. Квитанции отправляются автоматически и не доказывают применение учётных данных.

## Подключение Go Agent

Идентификация использует app_id, app_secret, org_id и стабильный instance_id; доступ определяется политиками приложения. Пути и действия задаются локально: state_file хранит последние пароли, event_file добавляет события без секретов, delivery задаёт вывод, rules — файлы, шаблоны и reload/restart либо фиксированные скрипты. После уведомления Agent получает и сохраняет актуальный пароль, атомарно заменяет файлы, затем выполняет действие. При сбое доставка повторяется. В rules используйте credentials[].key из get_accounts; ключ подписки включает ID аккаунта. Пустой rules записывает файл для каждого ключа.

Локальные rules задают файлы, JSON/EnvironmentFile или доверенные шаблоны и действие systemd reload/restart либо фиксированный исполняемый файл. Скрипты получают JSON через stdin, используют фиксированные аргументы и таймаут и проверяют применение перед успешным завершением. Core не расширяет эти возможности. После изменения приватной конфигурации перезапустите Agent.

Загруженная конфигурация уже содержит идентификацию Agent и параметры доставки. В rules укажите ID учётных записей приложения, обновление конфигурации, применение изменений и проверку рабочего соединения. allow_account_switch использует одно правило для ротации A/B в обоих направлениях. Необязательный credential_check проверяет новый вход до изменения файлов. Для путей состояния, событий, Socket и интервала сверки 300 секунд есть значения по умолчанию. Пустой rules создаёт файл для каждой учётной записи.

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

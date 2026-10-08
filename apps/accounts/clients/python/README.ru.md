# JumpServer PAM Python SDK / Agent

Python 3.9+ предоставляет SDK политик учётных данных. Go jms-pam-agent доставляет данные через локальные файлы, фиксированные действия или локальный Socket без Python. Запуск на переднем плане поддерживается в Linux, macOS и Windows; встроенная установка systemd доступна только в Linux.

<!-- agent-doc:start -->

## Подключение Go Agent

Подготовьте Linux с systemd и пользователем приложения. Скачайте jms_pam_agent.json из мастера, соберите или получите бинарный файл Go и установите со стабильным уникальным ID. Локальная конфигурация: /etc/jms-pam-agent/agent.json. Имя службы всегда jms-pam-agent.

```bash
cd apps/accounts/clients/go
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
chmod 0600 ./jms_pam_agent.json
sudo /usr/local/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

Для встроенной установки нужны Linux и root. На macOS, Linux без root или Windows выберите JSON либо Socket в мастере и выполните команды init-local и run --local --config. Инициализируйте один раз и повторно используйте закрытую локальную конфигурацию; режим переднего плана не выполняет действия systemd.

`/etc/jms-pam-agent/agent.json`: `0600`; `state_file`, `event_file`, `delivery.delivery_root`, `delivery.socket_path`.

- JSON: `/opt/jumpserver-pam/credentials/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<credential-key>.env`
- Unix Socket: `/run/jms-pam-agent/agent.sock`

JSON доставляет файлы, EnvironmentFile работает с закреплённой службой systemd, Unix Socket предоставляет локальный API. Agent сохраняет доставленную ревизию после успеха, приложение — применённую после проверки и использования. Socket принадлежит пользователю приложения и имеет права 0600; запросы выполняются от этого пользователя.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<credential-key>.env
```

Unit systemd должен ссылаться на EnvironmentFile. reload допустим, если приложение перечитывает файл; он не добавляет новые переменные среды работающему процессу. Пути, пользователь, служба и действие закрепляются при установке; для расширения прав нужна переустановка.

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


### Локальный API и подтверждение

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

При чередующейся ротации проверьте реальное подключение, переключите пул и освободите старые соединения, затем подтвердите точные key, revision и account_id. Подписка на изменение учётных данных подтверждения не требует. При ошибке проверки соединения подтверждать нельзя.

```bash
/usr/local/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jms-pam-agent/agent.sock'
```

confirm нужен только чередующейся ротации. Подтверждение сначала сохраняется локально: confirmed означает приём Core, pending — последующую повторную попытку. Запись файла или перезапуск службы сами по себе не являются основанием для подтверждения.

### Устранение неполадок

```bash
sudo systemctl start jms-pam-agent
sudo systemctl status jms-pam-agent --no-pager
sudo journalctl -u jms-pam-agent -n 100 --no-pager
sudo systemctl restart jms-pam-agent
```

Agent синхронизируется при запуске, по соответствующим событиям и каждые 300 секунд. Ошибки сети сохраняют последние полученные разрешённые учётные данные. Отклонение идентификатора или прав блокирует выдачу через Socket; успешная подписанная синхронизация восстанавливает доступ. Доставленные файлы остаются. SIGINT/SIGTERM закрывают службу, соединения и поток чтения.

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Подключение Python SDK

Создайте и привяжите политику, разрешите аккаунты ресурсов и скачайте jms_pam_config.py в мастере приложения. Требуется Python 3.9+. Используйте команду установки из репозитория ниже или python3 -m pip install . в распакованном каталоге SDK.

```bash
python3 -m pip install ./apps/accounts/clients/python
```

Поместите jms_pam_config.py рядом с приложением. client_options содержит данные идентификации: не сохраняйте их в репозитории или журналах. Каждый экземпляр использует стабильный уникальный instance_id. get_credential принимает ровно один селектор: account_id для аккаунта или key для политики ротации.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


with Client(instance_id=instance_id, **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### События и применение учётных данных

Обрабатывайте первоначальный/повторный snapshot и credential.updated. Пример разделяет subscription и alternating_rotation. Реализуйте apply_credential: проверьте соединение, переключите пул и освободите старые соединения. Заглушка вызывает исключение и не позволяет подтвердить ещё не применённые данные.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def apply_credential(credential):
    raise NotImplementedError('Реализуйте и проверьте переключение учётных данных приложения')


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

При чередующейся ротации проверьте реальное подключение, переключите пул и освободите старые соединения, затем подтвердите точные key, revision и account_id. Подписка на изменение учётных данных подтверждения не требует. При ошибке проверки соединения подтверждать нельзя.

SDK автоматически пытается отправить квитанцию received перед передачей бизнес-события. Приложению не нужно отправлять её повторно. Квитанция означает только чтение события, а не применение учётных данных, и не заменяет подтверждение. Сверяйте начальный снимок и снимки при переподключении; snapshot и pong не требуют квитанций.

## Обработчики событий

Инициализируйте локальное состояние перед запуском подписки. Python и Node.js используют подкласс, Go — EventHandlers, Java — CredentialEventListener. Реализуйте переключение соединений в примере. Прежний API сохранён.

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

Начальный snapshot, snapshot после переподключения и credential.updated получают данные по режиму политики и последовательно вызывают обработчик. Чтение использует очередь на 128 событий; заполнение создаёт обратное давление. Ошибки получения и применения повторяются с экспоненциальной задержкой 1–30 секунд и новым запросом. Новое событие заменяет повтор для той же цели; snapshot обновляет область, отзыв и изменение конфигурации отменяют повторы. Обработчики должны быть идемпотентными. Наблюдатели и отзыв автоматически не повторяются; команды требуют захвата выполнения. received означает чтение; SDK не подтверждает ротацию автоматически. События старых ревизий не отменяют ожидающее получение более новой ревизии.

`watch_events(stop_event=...)` / `start_events(stop_event=...)`; `stop_events()` / `close()`

watch_events ждёт остановки; start_events не гарантирует начальную синхронизацию. Дождитесь готовности приложения. Один слушатель на клиент. stop_events и close ждут обработчик; он может остановить свой клиент. clone заново создаёт состояние подкласса.

### Последние учётные данные и недоступность сервера

Сначала выполняется запрос API. Успешный ответ заменяет сохранённые последние данные; старая версия не заменяет новую, срок истечения по времени отсутствует. Только тайм-аут, сетевой сбой или HTTP 5xx позволяют вернуть последний успешный результат того же селектора с признаком локального источника. Без прежнего значения возвращается исходная ошибка. SDK хранит данные в памяти клиента до обновления, отзыва или закрытия; clone и перезапуск начинают с пустого состояния. Agent использует защищённое локальное состояние. HTTP 401/403/404 или client_upgrade_required очищают данные SDK и вызывают ошибку; некорректный успешный ответ также ошибочен. Отзыв удаляет соответствующие данные, snapshot — данные вне разрешений. Изменение конфигурации сохраняет значения до проверки следующего snapshot. Agent применяет явный отзыв и сокращение области snapshot до HTTP-синхронизации, сохраняет эту область и блокирует соответствующую локальную выдачу даже при сбое сервера или после перезапуска. Ответ credential_not_found (HTTP 400) также удаляет сохранённые значения SDK. Прямой pull по account_id всегда требует ответа API; снимок push не подтверждает право на кешированное значение pull.

- `credential.from_local`
- `get_credential(key=..., allow_local_fallback=False)` / `get_credential(account_id=..., allow_local_fallback=False)`

При управляемой подписке snapshot и credential.updated автоматически получают данные, заменяют локальное значение и вызывают обработчик. Ошибка обновления сохраняет прежнее значение и запускает повтор. Agent также получает данные по уведомлениям и сохраняет их при сбоях сервера. Для обновления и ручного переключения используйте вызовы с обязательным запросом API ниже. Сохранённое значение не считается новой полученной версией и не подтверждает ротацию автоматически.

При простое ping отправляется каждые 10 секунд. Около 30 секунд без сообщений вызывают переподключение с задержкой 1–30 секунд и новой подписью. snapshot восстанавливает текущее состояние без воспроизведения истории.



### Команды приложения

Получайте ожидающие команды через list_application_commands и запрашивайте выполнение через execute_application_command(event, handler). Обработчик запускается лишь при accepted: true. Переключение проверяет аккаунт и ревизию, применяет данные и подтверждает их; перезапуск проверяет работоспособность до сообщения об успехе. Ошибка отчёта о неудаче не скрывает исходное исключение.

### Основные методы

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `watch_events(stop_event=...)` / `start_events(stop_event=...)` / `stop_events()`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

with или close закрывают HTTP-сеанс и поток событий, clone создаёт независимый сеанс. Ошибки HTTP, сети, аутентификации и разбора вызывают PAMError с code, status_code, detail и original_error. Повторяйте временные ошибки на границе приложения, явно обрабатывайте отказ доступа и не записывайте учётные данные.

Новый код использует методы snake_case с именованными аргументами и атрибуты dataclass. Старый API объектов запросов credential.v1 сохранён с DeprecationWarning. SDK и Agent используют протокол версии 1, а sync_agent принимает KnownRevision для сохранённых и доставленных ревизий.

<!-- sdk-doc:end -->

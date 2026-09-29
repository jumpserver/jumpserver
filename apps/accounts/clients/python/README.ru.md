# JumpServer PAM Python SDK / Agent

Python 3.9+ предоставляет SDK политик учётных данных и Linux Agent. SDK использует AK/SK приложения, а Agent доставляет данные локально для приложений на любых языках.

<!-- agent-doc:start -->

## Подключение Linux Agent

Подготовьте Linux с systemd, Python 3.9+ и пользователем приложения. Привяжите приложение к политике и разрешите аккаунты; для чередующейся ротации нужны оба. В мастере подключения выберите Agent, пользователя, путь установки и способ доставки, затем скачайте jms_pam_agent.json. Установите скачанный SDK и выполните команду ниже для стандартного пути. Каждому экземпляру нужен стабильный уникальный ID.

```bash
sudo python3 -m venv /opt/jumpserver-pam/venv
sudo /opt/jumpserver-pam/venv/bin/python -m pip install '<sdk-directory>'
sudo /opt/jumpserver-pam/venv/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

Ниже указаны стандартные пути. configuration-id берётся из загрузочного файла, credential-key — из политики. Используйте фактический путь установки. Файл содержит AK/SK: ограничьте чтение, удалите скачанный файл после установки и защитите установленную конфигурацию.

- JSON: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env`
- Unix Socket: `/run/jumpserver-pam/<configuration-id>/agent.sock`

JSON доставляет файлы, EnvironmentFile работает с закреплённой службой systemd, Unix Socket предоставляет локальный API. Agent сохраняет доставленную ревизию после успеха, приложение — применённую после проверки и использования. Socket принадлежит пользователю приложения и имеет права 0600; запросы выполняются от этого пользователя.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env
```

Unit systemd должен ссылаться на EnvironmentFile. reload допустим, если приложение перечитывает файл; он не добавляет новые переменные среды работающему процессу. Пути, пользователь, служба и действие закрепляются при установке; для расширения прав нужна переустановка.

### Локальный API и подтверждение

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

При чередующейся ротации проверьте реальное подключение, переключите пул и освободите старые соединения, затем подтвердите точные key, revision и account_id. Подписка на изменение учётных данных подтверждения не требует. При ошибке проверки соединения подтверждать нельзя.

```bash
/opt/jumpserver-pam/venv/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jumpserver-pam/<configuration-id>/agent.sock'
```

confirm нужен только чередующейся ротации. Подтверждение сначала сохраняется локально: confirmed означает приём Core, pending — последующую повторную попытку. Запись файла или перезапуск службы сами по себе не являются основанием для подтверждения.

### Устранение неполадок

```bash
sudo systemctl status 'jms-pam-agent-<configuration-id>.service' --no-pager
sudo journalctl -u 'jms-pam-agent-<configuration-id>.service' -n 100 --no-pager
sudo systemctl restart 'jms-pam-agent-<configuration-id>.service'
```

Agent синхронизируется при запуске, по соответствующим событиям и каждые 300 секунд. Ошибки сети сохраняют разрешённый кэш. Отклонение идентификатора или прав блокирует выдачу через Socket; успешная подписанная синхронизация восстанавливает доступ. Доставленные файлы остаются. SIGINT/SIGTERM закрывают службу, соединения и поток чтения.

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
from jms_pam_config import client_options


with Client(instance_id="app-node-1", **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### События и применение учётных данных

Обрабатывайте первоначальный/повторный snapshot и credential.updated. Пример разделяет subscription и alternating_rotation. Реализуйте apply_credential: проверьте соединение, переключите пул и освободите старые соединения. Заглушка вызывает исключение и не позволяет подтвердить ещё не применённые данные.

```python
from jms_pam import Client
from jms_pam_config import client_options


def apply_credential(credential):
    raise NotImplementedError('Реализуйте и проверьте переключение учётных данных приложения')


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

При чередующейся ротации проверьте реальное подключение, переключите пул и освободите старые соединения, затем подтвердите точные key, revision и account_id. Подписка на изменение учётных данных подтверждения не требует. При ошибке проверки соединения подтверждать нельзя.

SDK автоматически пытается отправить квитанцию received перед передачей бизнес-события. Приложению не нужно отправлять её повторно. Квитанция означает только чтение события, а не применение учётных данных, и не заменяет подтверждение. Сверяйте начальный снимок и снимки при переподключении; snapshot и pong не требуют квитанций.

### Команды приложения

Получайте ожидающие команды через list_application_commands и запрашивайте выполнение через execute_application_command(event, handler). Обработчик запускается лишь при accepted: true. Переключение проверяет аккаунт и ревизию, применяет данные и подтверждает их; перезапуск проверяет работоспособность до сообщения об успехе. Ошибка отчёта о неудаче не скрывает исходное исключение.

### Основные методы

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

with или close закрывают HTTP-сеанс и поток событий, clone создаёт независимый сеанс. Ошибки HTTP, сети, аутентификации и разбора вызывают PAMError с code, status_code, detail и original_error. Повторяйте временные ошибки на границе приложения, явно обрабатывайте отказ доступа и не записывайте учётные данные.

Новый код использует методы snake_case с именованными аргументами и атрибуты dataclass. Старый API объектов запросов credential.v1 сохранён с DeprecationWarning. SDK и Agent используют протокол версии 1, а sync_agent принимает KnownRevision для кэшированных и доставленных ревизий.

<!-- sdk-doc:end -->

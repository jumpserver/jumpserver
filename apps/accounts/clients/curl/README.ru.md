# cURL — Руководство по использованию

Этот каталог содержит HTTP-скрипт с подписью для диагностики прежнего API account-secret. Для интеграции приложения используйте SDK Python, Go, Java или Node.js.

## Требования

- Bash / cURL / OpenSSL / base64
- `demo.sh`

Нужны Bash, cURL, OpenSSL и base64. Измените ASSET и ACCOUNT и убедитесь, что подписанный запрос закодирован точно так же, как запрос, отправляемый cURL.

## Настройка и запуск

Создайте приложение в разделе управления приложениями и разрешите ему целевые аккаунты ресурсов. Укажите адрес, AK/SK приложения и ID организации ниже. Перед запуском замените все заполнители реальными значениями.

```bash
cd apps/accounts/clients/curl
export API_URL='https://jumpserver.example.com'
export API_KEY_ID='<app-id>'
export API_KEY_SECRET='<app-secret>'
export ORG_ID='<org-id>'

bash demo.sh
```

По умолчанию запрашиваются ресурс ubuntu_docker и аккаунт root. Замените их разрешёнными именами в коде. Команды выполняются из корня репозитория. Вывод содержит секреты; не направляйте его в журналы приложения.

## Запрос и ответ

```http
GET /api/v1/accounts/integration-applications/account-secret/?asset=ubuntu_docker&account=root
```

```json
{"id":"<app-id>","secret":"<account-secret>"}
```

id обозначает приложение, а не ревизию аккаунта. Значение secret: null может быть следствием настройки просмотра секретов на сервере. Примеры не получают события учётных данных, не сообщают применённые ревизии и не выполняют команды приложения.

## Устранение неполадок

При 401 проверьте AK/SK, организацию, время хоста и подписанный URL. При 403 — состояние приложения и разрешения аккаунта, при 400 — выбор ресурса/аккаунта и кодирование URL. Не записывайте секреты и заголовки Authorization; имена должны совпадать с разрешёнными ресурсами.

## Подключение к политикам учётных данных

Подробности подписи и таблица протокола ниже предназначены для диагностики. Для политик учётных данных используйте методы SDK или Python Agent через JSON-файлы, EnvironmentFile или Unix Socket.

| HTTP | API | JSON / query |
| --- | --- | --- |
| GET | `/api/v1/accounts/credential-client/credential/` | `instance_id`, `key` / `account_id` |
| POST | `/api/v1/accounts/credential-client/confirm/` | `instance_id`, `key`, `revision`, `account_id` |
| GET | `/api/v1/accounts/credential-client/commands/` | `instance_id` |
| POST | `/api/v1/accounts/credential-client/command-result/` | `instance_id`, `command_id`, `status`, `error_code` |
| WebSocket | `/ws/accounts/credential-events/` | `instance_id` |

Вычисляйте подпись HMAC-SHA256 в указанном порядке заголовков. request-target включает кодированный путь и запрос, Digest содержит SHA-256 фактического тела, X-JMS-Request-ID — уникальный UUID, Date — время HTTP UTC. Укажите X-JMS-Client-Version, X-JMS-Protocol-Version: 1 и X-JMS-Config-Schema-Version: 0 для SDK. API и WebSocket используют AK/SK приложения и стабильный уникальный instance_id; обновляйте подпись для каждого запроса и переподключения.

```text
(request-target) accept date digest x-jms-request-id x-jms-org
x-jms-client-version x-jms-protocol-version x-jms-config-schema-version
```

При чередующейся ротации проверьте реальное подключение, переключите пул и освободите старые соединения, затем подтвердите точные key, revision и account_id. Подписка на изменение учётных данных подтверждения не требует. При ошибке проверки соединения подтверждать нельзя.

received означает только чтение события. Перед обработкой события с event_id отправьте received по тому же WebSocket; snapshot и pong квитанции не требуют. При каждом подключении и переподключении сверяйте снимок, обрабатывайте credential.updated, отзыв разрешений и изменения конфигурации.

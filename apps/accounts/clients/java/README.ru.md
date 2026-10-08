# JumpServer PAM Java SDK

SDK соответствует функциям Python SDK политик учётных данных: получение по разрешённому аккаунту или политике ротации, подтверждение применённых версий, события, команды и синхронизация Agent. URL, HMAC-подпись, Digest, дата UTC, ID запроса и заголовки формируются автоматически.

## Требования

- JDK 11+ / Maven / Jackson
- `src/main/java/org/jumpserver/pam/Demo.java`

## Настройка и запуск

Установите исходный SDK и задайте параметры ниже. Разрешите аккаунты для pull в управлении приложениями; привязывайте политики только при необходимости push или ротации. Получите AK/SK и ID организации из материалов подключения. Замените шаблонные значения и защитите секреты развёртывания. Каждой реплике нужен стабильный уникальный ID. Укажите только один селектор: ID аккаунта или key политики.

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

SDK устанавливаются из исходного кода этого репозитория и ещё не опубликованы в общедоступных реестрах пакетов. Замените /path/to/jumpserver абсолютным путём. Команды установки Go и Node.js выполняйте в каталоге приложения; зависимость Java добавьте в pom.xml приложения. Локальные импорты из примеров замените импортами пакетов ниже.

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

## Запрос и ответ

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

## Обработчики событий

Инициализируйте локальное состояние перед запуском подписки. Python и Node.js используют подкласс, Go — EventHandlers, Java — CredentialEventListener. Реализуйте переключение соединений в примере. Прежний API сохранён.

```java
package org.jumpserver.pam;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.jumpserver.pam.Models.Credential;
import org.jumpserver.pam.Models.Event;

/** Replace the business hook before running. Listener methods run serially. */
public final class HooksDemo implements CredentialEventListener {
  private final Client client;
  private final Map<String, Credential> credentials = new HashMap<>();
  private final Map<String, String> modes = new HashMap<>();

  public HooksDemo(Client client) {
    this.client = client;
  }

  @Override
  public void onEvent(Event event) {
    List<Event> updates = List.of(event);
    if (event.getEvent().equals("snapshot")) {
      modes.clear();
      updates = event.getCredentials();
    }
    if (event.getEvent().equals("snapshot") || event.getEvent().equals("credential.updated"))
      for (Event update : updates) modes.put(update.getKey(), update.getCredentialMode());
    if (event.getEvent().equals("snapshot"))
      credentials.keySet().removeIf(key -> !modes.containsKey(key)); // Also release connections.
    // Use executeApplicationCommand for commands; see EventsDemo.
  }

  @Override
  public void onCredentialChanged(Credential credential) {
    applyCredential(credential);
    if ("alternating_rotation".equals(modes.get(credential.getKey())))
      client.confirmCredential(
          credential.getKey(), credential.getRevision(), credential.getAccount().getId());
    credentials.put(credential.getKey(), credential);
  }

  private void applyCredential(Credential credential) {
    throw new UnsupportedOperationException(
        "Implement connection validation, pool switching and old connection cleanup");
  }

  @Override
  public void onCredentialRevoked(Event event) {
    credentials.remove(event.getKey()); // Also release affected connections.
  }

  public static void main(String[] args) throws InterruptedException {
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
      try {
        client.watchEvents(new HooksDemo(client));
      } finally {
        try {
          Runtime.getRuntime().removeShutdownHook(stop);
        } catch (IllegalStateException ignored) {
        }
      }
    }
  }
}
```

Начальный snapshot, snapshot после переподключения и credential.updated получают данные по режиму политики и последовательно вызывают обработчик. Чтение использует очередь на 128 событий; заполнение создаёт обратное давление. Ошибки получения и применения повторяются с экспоненциальной задержкой 1–30 секунд и новым запросом. Новое событие заменяет повтор для той же цели; snapshot обновляет область, отзыв и изменение конфигурации отменяют повторы. Обработчики должны быть идемпотентными. Наблюдатели и отзыв автоматически не повторяются; команды требуют захвата выполнения. received означает чтение; SDK не подтверждает ротацию автоматически. События старых ревизий не отменяют ожидающее получение более новой ревизии.

`watchEvents(listener)` / `startEvents(listener)`; `stop()` / `close()` / `awaitTermination()`

watchEvents ждёт в вызывающем потоке; startEvents не гарантирует синхронизацию. Один слушатель на клиент. close ждёт обработчик, который может закрыть свой клиент. awaitTermination вызывается извне.

### Последние учётные данные и недоступность сервера

Сначала выполняется запрос API. Успешный ответ заменяет сохранённые последние данные; старая версия не заменяет новую, срок истечения по времени отсутствует. Только тайм-аут, сетевой сбой или HTTP 5xx позволяют вернуть последний успешный результат того же селектора с признаком локального источника. Без прежнего значения возвращается исходная ошибка. SDK хранит данные в памяти клиента до обновления, отзыва или закрытия; clone и перезапуск начинают с пустого состояния. Agent использует защищённое локальное состояние. HTTP 401/403/404 или client_upgrade_required очищают данные SDK и вызывают ошибку; некорректный успешный ответ также ошибочен. Отзыв удаляет соответствующие данные, snapshot — данные вне разрешений. Изменение конфигурации сохраняет значения до проверки следующего snapshot. Agent применяет явный отзыв и сокращение области snapshot до HTTP-синхронизации, сохраняет эту область и блокирует соответствующую локальную выдачу даже при сбое сервера или после перезапуска. Ответ credential_not_found (HTTP 400) также удаляет сохранённые значения SDK. Прямой pull по account_id всегда требует ответа API; снимок push не подтверждает право на кешированное значение pull.

- `credential.isFromLocal()`
- `getCredential(key, false)` / `getCredentialByAccountId(accountId, false)`

При управляемой подписке snapshot и credential.updated автоматически получают данные, заменяют локальное значение и вызывают обработчик. Ошибка обновления сохраняет прежнее значение и запускает повтор. Agent также получает данные по уведомлениям и сохраняет их при сбоях сервера. Для обновления и ручного переключения используйте вызовы с обязательным запросом API ниже. Сохранённое значение не считается новой полученной версией и не подтверждает ротацию автоматически.

При простое ping отправляется каждые 10 секунд. Около 30 секунд без сообщений вызывают переподключение с задержкой 1–30 секунд и новой подписью. snapshot восстанавливает текущее состояние без воспроизведения истории.



## События и применение учётных данных

Обрабатывайте начальный snapshot, снимки переподключения и credential.updated. Полный пример поддерживает subscription, alternating_rotation и команды. Реализуйте проверку реального подключения, переключение пула и освобождение прежних соединений. Заглушка вызывает исключение и запрещает подтверждение до применения. Удаляйте из состояния приложения отсутствующие в снимках аккаунты и обрабатывайте отзыв доступа.

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
    Credential credential = client.getCredential(event.getKey(), false);
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
                && !update.getAccountId().isEmpty() && !update.getKey().isEmpty()) {
              String key = update.getKey();
              if (!key.endsWith(":" + update.getAccountId())) key += ":" + update.getAccountId();
              credential = client.getCredential(key, false);
            }
            else if (update.getCredentialMode().equals("alternating_rotation")
                && !update.getKey().isEmpty())
              credential = client.getCredential(update.getKey(), false);
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

При чередующейся ротации проверьте реальное подключение, переключите пул и освободите старые соединения, затем подтвердите точные key, revision и account_id. Подписка на изменение учётных данных подтверждения не требует. При ошибке проверки соединения подтверждать нельзя.

## Команды приложения

Опрос, получение права выполнения и отчёт о результате используют методы SDK. Обработчик выполняется только после принятия заявки. Переключение проверяет версию и аккаунт, применяет и подтверждает; перезапуск проверяет работоспособность после запуска. Сообщайте об успехе после завершения. Ошибка отчёта сохраняет исходное исключение обработчика.

## Основные методы

- `getCredential(key)`
- `getCredentialByAccountId(accountId)`
- `getCredential(key, false) / getCredentialByAccountId(accountId, false)`
- `confirmCredential(key, revision, accountId)`
- `watchCredentialEvents()`
- `watchEvents(listener) / startEvents(listener)`
- `EventSubscription.stop() / close() / awaitTermination()`
- `listApplicationCommands()`
- `reportApplicationCommandResult(commandId, status, errorCode)`
- `executeApplicationCommand(event, handler)`
- `syncAgent(credentials, deliveredCredentials, configDigest, syncStatus, syncError)`
- `clone() / close()`

## Устранение неполадок

Ошибки HTTP, сети, аутентификации и декодирования представлены типом ошибки SDK с кодом и HTTP-статусом. Закрывайте потоки и клиенты после использования; жизненные циклы копий независимы. Повторяйте временные сбои на уровне приложения и не записывайте секреты или заголовки авторизации.

`PAMException`

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

# JumpServer PAM Go SDK

SDK соответствует функциям Python SDK политик учётных данных: получение по разрешённому аккаунту или политике ротации, подтверждение применённых версий, события, команды и синхронизация Agent. URL, HMAC-подпись, Digest, дата UTC, ID запроса и заголовки формируются автоматически.

## Требования

- Go 1.23+ / coder/websocket
- `cmd/demo/main.go`

## Настройка и запуск

Установите исходный SDK и задайте параметры ниже. Разрешите аккаунты и привяжите политики в управлении приложениями; получите AK/SK и ID организации из материалов подключения. Замените шаблонные значения и защитите секреты развёртывания. Каждой реплике нужен стабильный уникальный ID. Укажите только один селектор: ID аккаунта или key политики.

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

SDK устанавливаются из исходного кода этого репозитория и ещё не опубликованы в общедоступных реестрах пакетов. Замените /path/to/jumpserver абсолютным путём. Команды установки Go и Node.js выполняйте в каталоге приложения; зависимость Java добавьте в pom.xml приложения. Локальные импорты из примеров замените импортами пакетов ниже.

```bash
go mod edit -replace=github.com/jumpserver/jumpserver/apps/accounts/clients/go=/path/to/jumpserver/apps/accounts/clients/go
go get github.com/jumpserver/jumpserver/apps/accounts/clients/go@v0.0.0
```

```go
import pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
```

## Запрос и ответ

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

## События и применение учётных данных

Обрабатывайте начальный snapshot, снимки переподключения и credential.updated. Полный пример поддерживает subscription, alternating_rotation и команды. Реализуйте проверку реального подключения, переключение пула и освобождение прежних соединений. Заглушка вызывает исключение и запрещает подтверждение до применения. Удаляйте из кеша отсутствующие в снимках аккаунты и обрабатывайте отзыв доступа.

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

При чередующейся ротации проверьте реальное подключение, переключите пул и освободите старые соединения, затем подтвердите точные key, revision и account_id. Подписка на изменение учётных данных подтверждения не требует. При ошибке проверки соединения подтверждать нельзя.

## Команды приложения

Опрос, получение права выполнения и отчёт о результате используют методы SDK. Обработчик выполняется только после принятия заявки. Переключение проверяет версию и аккаунт, применяет и подтверждает; перезапуск проверяет работоспособность после запуска. Сообщайте об успехе после завершения. Ошибка отчёта сохраняет исходное исключение обработчика.

## Основные методы

- `GetCredential(ctx, CredentialSelector{Key: ...})`
- `GetCredential(ctx, CredentialSelector{AccountID: ...})`
- `ConfirmCredential(ctx, key, revision, accountID)`
- `WatchCredentialEvents(ctx, handler)`
- `ListApplicationCommands(ctx)`
- `ReportApplicationCommandResult(ctx, commandID, status, errorCode)`
- `ExecuteApplicationCommand(ctx, event, handler)`
- `SyncAgent(ctx, AgentSyncOptions{...})`
- `Clone() / Close()`

## Устранение неполадок

Ошибки HTTP, сети, аутентификации и декодирования представлены типом ошибки SDK с кодом и HTTP-статусом. Закрывайте потоки и клиенты после использования; жизненные циклы копий независимы. Повторяйте временные сбои на уровне приложения и не записывайте секреты или заголовки авторизации.

`PAMError`

Все SDK используют протокол версии 1; конфигурация Agent — схему версии 1. Ответ client_upgrade_required (HTTP 426) требует проверки совместимости и обновления. Неизвестные необязательные поля и уведомления допустимы; неподдерживаемые политики нельзя применять или подтверждать. Квитанции отправляются автоматически и не доказывают применение учётных данных.

## Подключение Linux Agent

Синхронизация предназначена для реализаций Agent. Нужны идентификатор или source Agent и ID конфигурации; KnownRevision передаёт кешированные и доставленные версии. Установка Linux, выдача файлов и локальный API сейчас реализованы Python Agent, доступным приложениям на любом языке.

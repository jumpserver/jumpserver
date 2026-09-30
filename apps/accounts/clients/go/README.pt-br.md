# JumpServer PAM Go SDK

Este SDK acompanha o SDK Python de políticas de credenciais: consulta por conta autorizada ou política de rotação, confirmação de versões aplicadas, eventos, comandos e sincronização Agent. URL, assinatura HMAC, Digest, data UTC, ID de requisição e cabeçalhos são gerados automaticamente.

## Requisitos

- Go 1.23+ / coder/websocket
- `cmd/demo/main.go`

## Configurar e executar

Instale o SDK fonte e configure os valores abaixo. Autorize contas para pull em Gerenciamento de aplicações; vincule políticas somente quando precisar de push ou rotação. Obtenha AK/SK e ID da organização nos materiais de acesso. Substitua os exemplos e proteja os segredos de implantação. Cada réplica precisa de um ID estável e único. Use um só seletor: ID da conta ou key da política.

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

Os SDKs são instalados a partir deste repositório e ainda não foram publicados em registros públicos. Substitua /path/to/jumpserver por um caminho absoluto. Execute a instalação Go e Node.js no diretório da aplicação ou adicione a dependência Java ao pom.xml da aplicação. Substitua as importações locais dos exemplos pelas importações de pacote abaixo.

```bash
go mod edit -replace=github.com/jumpserver/jumpserver/apps/accounts/clients/go=/path/to/jumpserver/apps/accounts/clients/go
go get github.com/jumpserver/jumpserver/apps/accounts/clients/go@v0.0.0
```

```go
import pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
```

## Requisição e resposta

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

## Manipuladores de eventos

Inicialize o estado local antes de iniciar a escuta. Python e Node.js usam subclasses, Go usa EventHandlers e Java usa CredentialEventListener. Implemente a troca real de conexões do exemplo. A API anterior continua disponível.

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

type application struct {
	client      *pam.Client
	credentials map[string]pam.Credential
	modes       map[string]string
}

func (a *application) observe(ctx context.Context, event pam.Event) error {
	updates := []pam.Event{event}
	if event.Event == "snapshot" {
		clear(a.modes)
		updates = event.Credentials
	}
	for _, update := range updates {
		key := update.CredentialKey
		if key == "" {
			key = update.Key
		}
		if key != "" && (event.Event == "snapshot" || event.Event == "credential.updated") {
			a.modes[key] = update.CredentialMode
		}
	}
	if event.Event == "snapshot" {
		for key := range a.credentials {
			if _, ok := a.modes[key]; !ok {
				delete(a.credentials, key) /* Also release connections. */
			}
		}
	}
	// Use ExecuteApplicationCommand for command events; see cmd/events/main.go.
	return nil
}
func applyCredential(ctx context.Context, credential pam.Credential) error {
	return fmt.Errorf("implement connection validation, pool switching and old connection cleanup")
}
func (a *application) changed(ctx context.Context, credential pam.Credential) error {
	if err := applyCredential(ctx, credential); err != nil {
		return err
	}
	if a.modes[credential.Key] == "alternating_rotation" {
		if _, err := a.client.ConfirmCredential(ctx, credential.Key, credential.Revision, credential.Account.ID); err != nil {
			return err
		}
	}
	a.credentials[credential.Key] = credential
	return nil
}
func (a *application) revoked(ctx context.Context, event pam.Event) error {
	delete(a.credentials, event.CredentialKey) // Also release affected connections.
	return nil
}
func main() {
	client, err := pam.NewClient(pam.Options{Endpoint: os.Getenv("JMS_ENDPOINT"), AppID: os.Getenv("JMS_APP_ID"), AppSecret: os.Getenv("JMS_APP_SECRET"), InstanceID: os.Getenv("JMS_INSTANCE_ID"), OrgID: os.Getenv("JMS_ORG_ID")})
	if err != nil {
		log.Fatal("Invalid SDK configuration")
	}
	defer client.Close()
	app := &application{client: client, credentials: make(map[string]pam.Credential), modes: make(map[string]string)}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	err = client.WatchEvents(ctx, pam.EventHandlers{OnEvent: app.observe, OnCredentialChanged: app.changed, OnCredentialRevoked: app.revoked})
	if err != nil && !errors.Is(err, context.Canceled) {
		log.Printf("Event processing failed: %T", err)
	}
}
```

Os snapshot inicial e de reconexão e credential.updated consultam por modo e chamam o manipulador em série. A leitura usa uma fila limitada a 128 eventos; quando cheia, aplica contrapressão. Falhas de consulta ou aplicação tentam novamente com espera exponencial de 1–30 segundos e uma nova consulta. Atualizações substituem tentativas do mesmo destino; snapshot redefine o escopo e revogação ou configuração cancela tentativas. Os manipuladores devem ser idempotentes. Observadores e revogação não são repetidos automaticamente; comandos exigem reivindicação. received significa leitura; o SDK não confirma rotações automaticamente. Eventos de versões anteriores não cancelam a consulta pendente de uma versão mais recente.

`WatchEvents(ctx, handlers)` / `StartEvents(ctx, handlers)`; `Stop()` / `Wait()`; `context.CancelFunc`

WatchEvents espera na goroutine; StartEvents não garante a sincronização inicial. Um listener por cliente. Stop e Close cancelam; chame Wait fora do manipulador. Respeite o cancelamento do context.

### Credenciais mais recentes e indisponibilidade do servidor

A consulta solicita primeiro a API. Uma resposta válida substitui a credencial retida; versões antigas não sobrescrevem novas e não há expiração por tempo. Apenas tempo limite, falha de rede ou HTTP 5xx permite retornar o último valor do mesmo seletor com a marca local. Sem valor anterior, propaga o erro. O SDK mantém os valores na memória até atualização, revogação ou fechamento; clone e reinício começam vazios. O Agent conserva os valores em seu estado local protegido. HTTP 401/403/404 ou client_upgrade_required apagam os valores do SDK e falham; uma resposta de sucesso inválida também falha. Revogação remove as credenciais afetadas e snapshot remove as não autorizadas. Uma mudança de configuração conserva os valores até conferir o snapshot seguinte. O Agent aplica revogações explícitas e reduções de escopo do snapshot antes da sincronização HTTP, salva esse escopo e bloqueia as leituras locais afetadas mesmo durante falhas ou após reiniciar. Uma resposta credential_not_found (HTTP 400) também apaga os valores mantidos pelo SDK. O pull direto por account_id sempre exige uma resposta ativa da API; snapshots de push não autorizam valores de pull em cache.

- `credential.FromLocal`
- `GetCredentialFresh(ctx, selector)`

Com escuta gerenciada ativa, snapshot e credential.updated consultam automaticamente, substituem o valor e chamam o manipulador. Falha na atualização mantém o anterior e tenta novamente. O Agent também consulta após notificações e mantém os dados durante falhas do servidor. Use as chamadas que exigem a API abaixo para atualizar ou trocar conexões; uma credencial retida não é uma versão recém-obtida nem confirma rotações automaticamente.

Quando ocioso, envia ping a cada 10 segundos; cerca de 30 segundos sem mensagens causam reconexão, com espera exponencial de 1–30 segundos e nova assinatura. O snapshot restaura o estado atual sem reproduzir eventos passados.



## Eventos e aplicação de credenciais

Processe snapshot inicial ou de reconexão e credential.updated. O exemplo completo trata subscription, alternating_rotation e comandos. Implemente verificação de conexão real, troca do pool e liberação das conexões antigas. O marcador lança uma exceção e impede confirmar antes de aplicar. Remova do estado da aplicação contas ausentes dos snapshots e trate revogações.

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
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
	credential, err := client.GetCredentialFresh(ctx, pam.CredentialSelector{Key: event.CredentialKey})
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
			if update.CredentialMode == "subscription" && update.AccountID != "" && key != "" {
				if !strings.HasSuffix(key, ":"+update.AccountID) {
					key += ":" + update.AccountID
				}
				selector.Key = key
			} else if update.CredentialMode == "alternating_rotation" && key != "" {
				selector.Key = key
			} else {
				continue
			}
			credential, err := client.GetCredentialFresh(ctx, selector)
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

Na rotação alternada, valide uma conexão real, troque o pool e libere conexões antigas antes de confirmar exatamente key, revision e account_id. Assinaturas de alterações de credenciais não exigem confirmação. Falhas na verificação de conexão devem impedir a confirmação.

## Comandos de aplicação

Consulta, solicitação de execução e resultados usam métodos SDK. Apenas uma solicitação aceita executa o handler. A troca verifica versão e conta, aplica e confirma; o reinício reinicia e verifica a saúde. Informe sucesso ao concluir. Falhas no relatório preservam a exceção original do handler.

## Métodos comuns

- `GetCredential(ctx, CredentialSelector{Key: ...})`
- `GetCredential(ctx, CredentialSelector{AccountID: ...})`
- `GetCredentialFresh(ctx, selector)`
- `ConfirmCredential(ctx, key, revision, accountID)`
- `WatchEvents(ctx, EventHandlers{...}) / StartEvents(ctx, handlers)`
- `EventWatcher.Stop() / EventWatcher.Wait()`
- `WatchCredentialEvents(ctx, handler)`
- `ListApplicationCommands(ctx)`
- `ReportApplicationCommandResult(ctx, commandID, status, errorCode)`
- `ExecuteApplicationCommand(ctx, event, handler)`
- `SyncAgent(ctx, AgentSyncOptions{...})`
- `Clone() / Close()`

## Solução de problemas

Falhas HTTP, rede, autenticação e decodificação usam o tipo de erro SDK com código e estado HTTP. Feche fluxos e clientes após usar; clones têm ciclos de vida independentes. Repita falhas transitórias na aplicação e não registre segredos nem cabeçalhos de autenticação.

`PAMError`

Todos os SDKs usam protocolo versão 1; Agent usa esquema de configuração versão 1. Em client_upgrade_required (HTTP 426), verifique compatibilidade e atualize. Campos opcionais e notificações desconhecidos são tolerados; não aplique nem confirme políticas não suportadas. Os recibos são automáticos e não provam aplicação de credenciais.

## Integração com o Go Agent

A identidade usa app_id, app_secret, org_id e instance_id estável; as permissões seguem as políticas da aplicação. Caminhos e ações são locais: state_file mantém as senhas atuais, event_file registra eventos sem segredos, delivery define a saída padrão e rules define arquivos, modelos e reload/restart ou scripts fixos. Ao receber uma atualização, o Agent busca e salva a senha atual, substitui os arquivos atomicamente e executa a ação; falhas são tentadas novamente. Use credentials[].key de get_accounts nas regras; chaves de assinatura incluem o ID da conta. rules vazio grava um arquivo por chave.

As rules locais definem arquivos, JSON/EnvironmentFile ou modelos confiáveis e uma ação systemd reload/restart ou executável fixo. Scripts recebem JSON via stdin, usam argumentos fixos e prazo limitado, e verificam a aplicação antes de retornar sucesso. Core não pode ampliar essas capacidades. Reinicie o Agent após editar a configuração privada.

A identidade usa app_id, app_secret, org_id e instance_id estável; as permissões seguem as políticas da aplicação. Caminhos e ações são locais: state_file mantém as senhas atuais, event_file registra eventos sem segredos, delivery define a saída padrão e rules define arquivos, modelos e reload/restart ou scripts fixos. Ao receber uma atualização, o Agent busca e salva a senha atual, substitui os arquivos atomicamente e executa a ação; falhas são tentadas novamente. Use credentials[].key de get_accounts nas regras; chaves de assinatura incluem o ID da conta. rules vazio grava um arquivo por chave.

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

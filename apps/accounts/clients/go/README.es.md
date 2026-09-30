# JumpServer PAM Go SDK

Este SDK sigue las funciones del SDK Python de políticas de credenciales: obtener por cuenta autorizada o política de rotación, confirmar versiones aplicadas, escuchar eventos, procesar comandos y sincronizar Agent. URL, firma HMAC, Digest, fecha UTC, ID de solicitud y cabeceras se generan automáticamente.

## Requisitos

- Go 1.23+ / coder/websocket
- `cmd/demo/main.go`

## Configuración y ejecución

Instale el SDK fuente y configure los valores siguientes. Autorice las cuentas para pull en Administración de aplicaciones; vincule políticas solo si necesita push o rotación. Obtenga AK/SK e ID de organización de los materiales de acceso. Sustituya los ejemplos y proteja los secretos de despliegue. Cada réplica necesita un ID estable y único. Use un único selector: ID de cuenta o key de política.

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

Los SDK se instalan desde el código de este repositorio y aún no se han publicado en registros públicos. Sustituya /path/to/jumpserver por una ruta absoluta. Ejecute la instalación de Go y Node.js en el directorio de la aplicación o añada la dependencia Java al pom.xml de la aplicación. Sustituya las importaciones locales de los ejemplos por las importaciones de paquetes siguientes.

```bash
go mod edit -replace=github.com/jumpserver/jumpserver/apps/accounts/clients/go=/path/to/jumpserver/apps/accounts/clients/go
go get github.com/jumpserver/jumpserver/apps/accounts/clients/go@v0.0.0
```

```go
import pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
```

## Solicitud y respuesta

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

## Manejadores de eventos

Inicialice el estado local antes de escuchar. Python y Node.js usan métodos de subclase, Go EventHandlers y Java CredentialEventListener. Implemente el cambio real de conexiones del ejemplo. La API anterior sigue disponible.

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

Los snapshot iniciales y de reconexión y credential.updated obtienen credenciales por modo y llaman al manejador en serie. La lectura usa una cola limitada a 128 eventos; al llenarse aplica contrapresión. Los fallos de obtención o aplicación se reintentan con espera exponencial de 1–30 segundos y una nueva consulta. Las actualizaciones sustituyen reintentos del mismo destino; snapshot restablece el ámbito y revocaciones o cambios de configuración cancelan reintentos. Los manejadores deben ser idempotentes. Los observadores y revocaciones no se reintentan; los comandos requieren reclamar su ejecución. received indica lectura; el SDK no confirma rotaciones automáticamente. Los eventos de revisiones anteriores no cancelan la obtención pendiente de una revisión más reciente.

`WatchEvents(ctx, handlers)` / `StartEvents(ctx, handlers)`; `Stop()` / `Wait()`; `context.CancelFunc`

WatchEvents espera en la goroutine; StartEvents no garantiza la sincronización inicial. Un listener por cliente. Stop y Close cancelan; espere con Wait desde fuera del manejador. Respete la cancelación del context.

### Credenciales más recientes y fallos del servidor

La consulta solicita primero la API. Una respuesta exitosa reemplaza la credencial retenida; versiones antiguas no sobrescriben una nueva y no hay caducidad por tiempo. Solo un tiempo de espera, fallo de red o HTTP 5xx permite devolver el último valor del mismo selector con la marca de origen local. Sin valor previo se propaga el error. El SDK lo conserva en memoria hasta actualización, revocación o cierre; clone y reinicio comienzan vacíos. El Agent conserva sus credenciales en su estado local protegido. HTTP 401/403/404 o client_upgrade_required borran los valores del SDK y fallan; una respuesta exitosa inválida también falla. La revocación elimina las credenciales afectadas; snapshot elimina entradas fuera de autorización. Un cambio de configuración conserva los valores hasta comprobar el snapshot siguiente. El Agent aplica las revocaciones explícitas y las reducciones del ámbito del snapshot antes de sincronizar por HTTP, guarda ese ámbito y bloquea las lecturas locales afectadas incluso durante una caída o tras reiniciar. Una respuesta credential_not_found (HTTP 400) también elimina los valores conservados del SDK. La consulta pull directa por account_id siempre requiere una respuesta activa de la API; los snapshots de push no autorizan valores pull en caché.

- `credential.FromLocal`
- `GetCredentialFresh(ctx, selector)`

Con la escucha gestionada activa, snapshot y credential.updated consultan automáticamente la credencial actual, reemplazan el valor y llaman al manejador. Un fallo de actualización conserva el valor anterior y reintenta. El Agent también consulta tras una notificación y conserva sus datos durante fallos del servidor. Use las llamadas que requieren la API siguientes para actualizar o cambiar conexiones; un valor retenido no es una versión recién obtenida ni confirma rotaciones automáticamente.

En reposo se envía ping cada 10 segundos; unos 30 segundos sin mensajes provocan reconexión, con espera exponencial de 1–30 segundos y firma nueva. El snapshot restaura el estado actual, sin reproducir eventos históricos.



## Eventos y aplicación de credenciales

Procese snapshot inicial o de reconexión y credential.updated. El ejemplo completo maneja subscription, alternating_rotation y comandos. Implemente la validación de una conexión real, el cambio del pool y el cierre de conexiones anteriores. El marcador genera una excepción e impide confirmar antes de aplicar. Retire del estado de la aplicación las cuentas ausentes de los snapshots y procese las revocaciones.

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

En la rotación alternada, valide una conexión real, cambie el pool y cierre las conexiones anteriores antes de confirmar exactamente key, revision y account_id. Las suscripciones a cambios de credenciales no requieren confirmación. Un fallo de conexión debe impedir la confirmación.

## Comandos de aplicación

La consulta, reclamación de comandos y comunicación de resultados usan métodos SDK. Solo una reclamación aceptada ejecuta el handler. El cambio verifica versión y cuenta, aplica y confirma; el reinicio reinicia y comprueba el estado. Informe de éxito al terminar. Un fallo al informar conserva la excepción original del handler.

## Métodos habituales

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

## Solución de problemas

Los fallos HTTP, de red, autenticación y decodificación usan el tipo de error SDK con código y estado HTTP. Cierre flujos y clientes tras usarlos; los clones tienen ciclos de vida independientes. Reintente fallos transitorios en la aplicación y no registre secretos ni cabeceras de autenticación.

`PAMError`

Todos los SDK usan protocolo versión 1; Agent usa esquema de configuración versión 1. Ante client_upgrade_required (HTTP 426), verifique compatibilidad y actualice. Se toleran campos opcionales y notificaciones desconocidos; no aplique ni confirme políticas no soportadas. Los recibos se envían automáticamente y no prueban la aplicación de credenciales.

## Integración del Go Agent

La identidad usa app_id, app_secret, org_id e instance_id estable; la autorización sigue las políticas de la aplicación. Las rutas y acciones son locales: state_file conserva las contraseñas actuales, event_file añade eventos sin secretos, delivery define la salida y rules define archivos, plantillas y reload/restart o scripts fijos. Ante una actualización, el Agent obtiene y guarda la contraseña actual, reemplaza los archivos de forma atómica y ejecuta la acción; los fallos se reintentan. Use credentials[].key de get_accounts en rules; las claves de suscripción incluyen el ID de cuenta. rules vacío escribe un archivo por clave.

Las rules locales configuran archivos, JSON/EnvironmentFile o plantillas fiables y una acción systemd reload/restart o un ejecutable fijo. Los scripts reciben JSON por stdin, usan argumentos fijos y un tiempo límite, y verifican la aplicación antes de devolver éxito. Core no puede ampliar estas capacidades. Reinicie el Agent tras editar la configuración privada.

La identidad usa app_id, app_secret, org_id e instance_id estable; la autorización sigue las políticas de la aplicación. Las rutas y acciones son locales: state_file conserva las contraseñas actuales, event_file añade eventos sin secretos, delivery define la salida y rules define archivos, plantillas y reload/restart o scripts fijos. Ante una actualización, el Agent obtiene y guarda la contraseña actual, reemplaza los archivos de forma atómica y ejecuta la acción; los fallos se reintentan. Use credentials[].key de get_accounts en rules; las claves de suscripción incluyen el ID de cuenta. rules vacío escribe un archivo por clave.

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

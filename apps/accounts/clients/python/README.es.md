# JumpServer PAM Python SDK / Agent

Python 3.9+ proporciona el SDK de políticas de credenciales. jms-pam-agent en Go entrega credenciales mediante archivos locales, acciones fijas o Socket local sin Python. Se ejecuta en primer plano en Linux, macOS y Windows; la instalación systemd integrada es solo para Linux.

<!-- agent-doc:start -->

## Integración del Go Agent

Prepare Linux con systemd y el usuario de la aplicación. Descargue jms_pam_agent.json del asistente, compile u obtenga el binario Go e instálelo con un ID estable y único. La configuración local es /etc/jms-pam-agent/agent.json y el servicio fijo es jms-pam-agent.

```bash
cd apps/accounts/clients/go
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
chmod 0600 ./jms_pam_agent.json
sudo /usr/local/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

El instalador integrado requiere Linux y root. En macOS, Linux sin root o Windows, elija JSON o Socket en el asistente y siga init-local y run --local --config. Inicialice una vez y reutilice la configuración local privada; el modo en primer plano no realiza acciones systemd.

`/etc/jms-pam-agent/agent.json`: `0600`; `state_file`, `event_file`, `delivery.delivery_root`, `delivery.socket_path`.

- JSON: `/opt/jumpserver-pam/credentials/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<credential-key>.env`
- Unix Socket: `/run/jms-pam-agent/agent.sock`

Elija JSON para archivos, EnvironmentFile para un servicio systemd fijado en la instalación o Unix Socket para la API local. El Agent registra revisiones entregadas cuando finaliza la entrega; la aplicación valida y aplica antes de registrar la revisión aplicada. El socket pertenece al usuario configurado y tiene permisos 0600; haga las solicitudes con ese usuario.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<credential-key>.env
```

La unidad systemd debe referenciar EnvironmentFile. Use reload solo si la aplicación vuelve a leerlo; no introduce nuevas variables de entorno en un proceso existente. La instalación fija rutas, usuario, servicio y acción permitidos; ampliarlos exige reinstalar.

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


### API local y confirmación

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

En la rotación alternada, valide una conexión real, cambie el pool y cierre las conexiones anteriores antes de confirmar exactamente key, revision y account_id. Las suscripciones a cambios de credenciales no requieren confirmación. Un fallo de conexión debe impedir la confirmación.

```bash
/usr/local/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jms-pam-agent/agent.sock'
```

Solo la rotación alternada usa confirm. La confirmación local se guarda primero; confirmed significa que Core la aceptó y pending que se reintentará. No confirme solo porque se escribió un archivo o se reinició un servicio.

### Solución de problemas

```bash
sudo systemctl start jms-pam-agent
sudo systemctl status jms-pam-agent --no-pager
sudo journalctl -u jms-pam-agent -n 100 --no-pager
sudo systemctl restart jms-pam-agent
```

El Agent sincroniza al arrancar, ante eventos pertinentes y cada 300 segundos. Los fallos de red conservan las últimas credenciales autorizadas. Un rechazo de identidad o autorización bloquea la lectura por socket; una sincronización firmada correcta la restablece. Los archivos ya escritos se conservan. SIGINT/SIGTERM cierran servidor, conexiones e hilo lector.

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Integración del SDK de Python

Cree y vincule una política, autorice las cuentas y descargue jms_pam_config.py del asistente de acceso. Se requiere Python 3.9+. Instale desde el repositorio con el comando siguiente o ejecute python3 -m pip install . en el directorio SDK descargado.

```bash
python3 -m pip install ./apps/accounts/clients/python
```

Coloque jms_pam_config.py junto a la aplicación. client_options contiene material de identidad: no lo guarde en el repositorio ni en registros. Use un instance_id estable y único por réplica. get_credential admite exactamente un selector: account_id para cuentas autorizadas o key para una política de rotación.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


with Client(instance_id=instance_id, **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### Eventos y aplicación de credenciales

Procese tanto snapshot inicial o de reconexión como credential.updated. El ejemplo distingue subscription de alternating_rotation. Implemente apply_credential para validar una conexión real, cambiar el pool y cerrar conexiones anteriores. El marcador genera una excepción para impedir confirmar credenciales no aplicadas.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def apply_credential(credential):
    raise NotImplementedError('Implemente y verifique el cambio de credenciales de la aplicación')


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

En la rotación alternada, valide una conexión real, cambie el pool y cierre las conexiones anteriores antes de confirmar exactamente key, revision y account_id. Las suscripciones a cambios de credenciales no requieren confirmación. Un fallo de conexión debe impedir la confirmación.

El SDK envía automáticamente un recibo received, cuando es posible, antes de entregar un evento de negocio. La aplicación no debe enviarlo de nuevo. El recibo solo indica lectura, no aplicación de credenciales, y no sustituye la confirmación. Concilie snapshots iniciales y de reconexión; snapshot y pong no requieren recibo.

## Manejadores de eventos

Inicialice el estado local antes de escuchar. Python y Node.js usan métodos de subclase, Go EventHandlers y Java CredentialEventListener. Implemente el cambio real de conexiones del ejemplo. La API anterior sigue disponible.

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

Los snapshot iniciales y de reconexión y credential.updated obtienen credenciales por modo y llaman al manejador en serie. La lectura usa una cola limitada a 128 eventos; al llenarse aplica contrapresión. Los fallos de obtención o aplicación se reintentan con espera exponencial de 1–30 segundos y una nueva consulta. Las actualizaciones sustituyen reintentos del mismo destino; snapshot restablece el ámbito y revocaciones o cambios de configuración cancelan reintentos. Los manejadores deben ser idempotentes. Los observadores y revocaciones no se reintentan; los comandos requieren reclamar su ejecución. received indica lectura; el SDK no confirma rotaciones automáticamente. Los eventos de revisiones anteriores no cancelan la obtención pendiente de una revisión más reciente.

`watch_events(stop_event=...)` / `start_events(stop_event=...)`; `stop_events()` / `close()`

watch_events espera al cierre; start_events no garantiza la sincronización inicial. Espere a que la aplicación esté lista. Un listener por cliente; stop_events y close esperan al manejador activo. Puede detenerse desde el propio manejador. clone reinicializa la subclase.

### Credenciales más recientes y fallos del servidor

La consulta solicita primero la API. Una respuesta exitosa reemplaza la credencial retenida; versiones antiguas no sobrescriben una nueva y no hay caducidad por tiempo. Solo un tiempo de espera, fallo de red o HTTP 5xx permite devolver el último valor del mismo selector con la marca de origen local. Sin valor previo se propaga el error. El SDK lo conserva en memoria hasta actualización, revocación o cierre; clone y reinicio comienzan vacíos. El Agent conserva sus credenciales en su estado local protegido. HTTP 401/403/404 o client_upgrade_required borran los valores del SDK y fallan; una respuesta exitosa inválida también falla. La revocación elimina las credenciales afectadas; snapshot elimina entradas fuera de autorización. Un cambio de configuración conserva los valores hasta comprobar el snapshot siguiente. El Agent aplica las revocaciones explícitas y las reducciones del ámbito del snapshot antes de sincronizar por HTTP, guarda ese ámbito y bloquea las lecturas locales afectadas incluso durante una caída o tras reiniciar. Una respuesta credential_not_found (HTTP 400) también elimina los valores conservados del SDK. La consulta pull directa por account_id siempre requiere una respuesta activa de la API; los snapshots de push no autorizan valores pull en caché.

- `credential.from_local`
- `get_credential(key=..., allow_local_fallback=False)` / `get_credential(account_id=..., allow_local_fallback=False)`

Con la escucha gestionada activa, snapshot y credential.updated consultan automáticamente la credencial actual, reemplazan el valor y llaman al manejador. Un fallo de actualización conserva el valor anterior y reintenta. El Agent también consulta tras una notificación y conserva sus datos durante fallos del servidor. Use las llamadas que requieren la API siguientes para actualizar o cambiar conexiones; un valor retenido no es una versión recién obtenida ni confirma rotaciones automáticamente.

En reposo se envía ping cada 10 segundos; unos 30 segundos sin mensajes provocan reconexión, con espera exponencial de 1–30 segundos y firma nueva. El snapshot restaura el estado actual, sin reproducir eventos históricos.



### Comandos de aplicación

Use list_application_commands para consultar solicitudes pendientes y execute_application_command(event, handler) para reclamar su ejecución. Solo una reclamación aceptada ejecuta el handler. El de cambio verifica revisión y cuenta, aplica y confirma; el de reinicio reinicia y comprueba el estado. Informe de éxito solo al terminar. Un fallo al informar del resultado conserva la excepción original del handler.

### Métodos habituales

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `watch_events(stop_event=...)` / `start_events(stop_event=...)` / `stop_events()`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

El cliente cierra sesiones HTTP y flujos de eventos con with o close. clone crea una sesión independiente. Los fallos HTTP, de red, autenticación y decodificación generan PAMError con code, status_code, detail y original_error. Reintente errores transitorios en la aplicación, gestione los rechazos de autorización y no registre credenciales.

El código nuevo usa métodos snake_case con argumentos por nombre y atributos de dataclass. La API original credential.v1 sigue disponible con DeprecationWarning. SDK versión 1 usa el protocolo del Agent; sync_agent acepta KnownRevision para revisiones conservadas y entregadas.

<!-- sdk-doc:end -->

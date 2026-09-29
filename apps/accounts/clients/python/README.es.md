# JumpServer PAM Python SDK / Agent

Python 3.9+ proporciona el SDK de políticas de credenciales y el Agent para Linux. El SDK utiliza AK/SK de la aplicación; el Agent entrega credenciales localmente a aplicaciones de otros lenguajes.

<!-- agent-doc:start -->

## Integración del Agent para Linux

Prepare Linux con systemd, Python 3.9+ y el usuario de la aplicación. Vincule una política y autorice sus cuentas; la rotación alternada necesita ambas. En el asistente de acceso seleccione Agent, configure usuario, ruta y modo de entrega y descargue jms_pam_agent.json. Instale el directorio SDK descargado y ejecute el comando para la ruta predeterminada, sustituyendo los valores de ejemplo. Cada réplica necesita un ID estable y único.

```bash
sudo python3 -m venv /opt/jumpserver-pam/venv
sudo /opt/jumpserver-pam/venv/bin/python -m pip install '<sdk-directory>'
sudo /opt/jumpserver-pam/venv/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

Las rutas predeterminadas se muestran abajo. Obtenga configuration-id de la configuración inicial descargada y credential-key de la política. La ruta configurada puede ser distinta. El archivo inicial contiene AK/SK: restrinja su acceso, elimine la copia descargada tras instalar y proteja la configuración instalada.

- JSON: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env`
- Unix Socket: `/run/jumpserver-pam/<configuration-id>/agent.sock`

Elija JSON para archivos, EnvironmentFile para un servicio systemd fijado en la instalación o Unix Socket para la API local. El Agent registra revisiones entregadas cuando finaliza la entrega; la aplicación valida y aplica antes de registrar la revisión aplicada. El socket pertenece al usuario configurado y tiene permisos 0600; haga las solicitudes con ese usuario.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env
```

La unidad systemd debe referenciar EnvironmentFile. Use reload solo si la aplicación vuelve a leerlo; no introduce nuevas variables de entorno en un proceso existente. La instalación fija rutas, usuario, servicio y acción permitidos; ampliarlos exige reinstalar.

### API local y confirmación

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

En la rotación alternada, valide una conexión real, cambie el pool y cierre las conexiones anteriores antes de confirmar exactamente key, revision y account_id. Las suscripciones a cambios de credenciales no requieren confirmación. Un fallo de conexión debe impedir la confirmación.

```bash
/opt/jumpserver-pam/venv/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jumpserver-pam/<configuration-id>/agent.sock'
```

Solo la rotación alternada usa confirm. La confirmación local se guarda primero; confirmed significa que Core la aceptó y pending que se reintentará. No confirme solo porque se escribió un archivo o se reinició un servicio.

### Solución de problemas

```bash
sudo systemctl status 'jms-pam-agent-<configuration-id>.service' --no-pager
sudo journalctl -u 'jms-pam-agent-<configuration-id>.service' -n 100 --no-pager
sudo systemctl restart 'jms-pam-agent-<configuration-id>.service'
```

El Agent sincroniza al arrancar, ante eventos pertinentes y cada 300 segundos. Los fallos de red conservan la caché autorizada. Un rechazo de identidad o autorización bloquea la lectura por socket; una sincronización firmada correcta la restablece. Los archivos ya escritos se conservan. SIGINT/SIGTERM cierran servidor, conexiones e hilo lector.

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
from jms_pam_config import client_options


with Client(instance_id="app-node-1", **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### Eventos y aplicación de credenciales

Procese tanto snapshot inicial o de reconexión como credential.updated. El ejemplo distingue subscription de alternating_rotation. Implemente apply_credential para validar una conexión real, cambiar el pool y cerrar conexiones anteriores. El marcador genera una excepción para impedir confirmar credenciales no aplicadas.

```python
from jms_pam import Client
from jms_pam_config import client_options


def apply_credential(credential):
    raise NotImplementedError('Implemente y verifique el cambio de credenciales de la aplicación')


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

En la rotación alternada, valide una conexión real, cambie el pool y cierre las conexiones anteriores antes de confirmar exactamente key, revision y account_id. Las suscripciones a cambios de credenciales no requieren confirmación. Un fallo de conexión debe impedir la confirmación.

El SDK envía automáticamente un recibo received, cuando es posible, antes de entregar un evento de negocio. La aplicación no debe enviarlo de nuevo. El recibo solo indica lectura, no aplicación de credenciales, y no sustituye la confirmación. Concilie snapshots iniciales y de reconexión; snapshot y pong no requieren recibo.

### Comandos de aplicación

Use list_application_commands para consultar solicitudes pendientes y execute_application_command(event, handler) para reclamar su ejecución. Solo una reclamación aceptada ejecuta el handler. El de cambio verifica revisión y cuenta, aplica y confirma; el de reinicio reinicia y comprueba el estado. Informe de éxito solo al terminar. Un fallo al informar del resultado conserva la excepción original del handler.

### Métodos habituales

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

El cliente cierra sesiones HTTP y flujos de eventos con with o close. clone crea una sesión independiente. Los fallos HTTP, de red, autenticación y decodificación generan PAMError con code, status_code, detail y original_error. Reintente errores transitorios en la aplicación, gestione los rechazos de autorización y no registre credenciales.

El código nuevo usa métodos snake_case con argumentos por nombre y atributos de dataclass. La API original credential.v1 sigue disponible con DeprecationWarning. SDK versión 1 usa el protocolo del Agent; sync_agent acepta KnownRevision para revisiones en caché y entregadas.

<!-- sdk-doc:end -->

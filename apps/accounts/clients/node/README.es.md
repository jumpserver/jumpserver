# JumpServer PAM Node.js SDK

Este SDK sigue las funciones del SDK Python de políticas de credenciales: obtener por cuenta autorizada o política de rotación, confirmar versiones aplicadas, escuchar eventos, procesar comandos y sincronizar Agent. URL, firma HMAC, Digest, fecha UTC, ID de solicitud y cabeceras se generan automáticamente.

## Requisitos

- Node.js 20.3+ / ws
- `demo.js`

## Configuración y ejecución

Instale el SDK fuente y configure los valores siguientes. Autorice las cuentas para pull en Administración de aplicaciones; vincule políticas solo si necesita push o rotación. Obtenga AK/SK e ID de organización de los materiales de acceso. Sustituya los ejemplos y proteja los secretos de despliegue. Cada réplica necesita un ID estable y único. Use un único selector: ID de cuenta o key de política.

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

Los SDK se instalan desde el código de este repositorio y aún no se han publicado en registros públicos. Sustituya /path/to/jumpserver por una ruta absoluta. Ejecute la instalación de Go y Node.js en el directorio de la aplicación o añada la dependencia Java al pom.xml de la aplicación. Sustituya las importaciones locales de los ejemplos por las importaciones de paquetes siguientes.

```bash
npm install /path/to/jumpserver/apps/accounts/clients/node
```

```javascript
const { Client } = require('@jumpserver/pam')
// ESM: import { Client } from '@jumpserver/pam'
```

## Solicitud y respuesta

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

## Manejadores de eventos

Inicialice el estado local antes de escuchar. Python y Node.js usan métodos de subclase, Go EventHandlers y Java CredentialEventListener. Implemente el cambio real de conexiones del ejemplo. La API anterior sigue disponible.

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

Los snapshot iniciales y de reconexión y credential.updated obtienen credenciales por modo y llaman al manejador en serie. La lectura usa una cola limitada a 128 eventos; al llenarse aplica contrapresión. Los fallos de obtención o aplicación se reintentan con espera exponencial de 1–30 segundos y una nueva consulta. Las actualizaciones sustituyen reintentos del mismo destino; snapshot restablece el ámbito y revocaciones o cambios de configuración cancelan reintentos. Los manejadores deben ser idempotentes. Los observadores y revocaciones no se reintentan; los comandos requieren reclamar su ejecución. received indica lectura; el SDK no confirma rotaciones automáticamente. Los eventos de revisiones anteriores no cancelan la obtención pendiente de una revisión más reciente.

`watchEvents({signal})` / `startEvents({signal})`; `stopEvents()` / `await subscription.stop()` / `await subscription.done`

watchEvents no bloquea el bucle de eventos; startEvents no garantiza la sincronización inicial. Un listener por cliente. Los métodos async se esperan en serie y reciben AbortSignal. close cancela; espere stop() o done desde fuera. El manejador no debe esperar su propio done. clone devuelve Client.

### Credenciales más recientes y fallos del servidor

La consulta solicita primero la API. Una respuesta exitosa reemplaza la credencial retenida; versiones antiguas no sobrescriben una nueva y no hay caducidad por tiempo. Solo un tiempo de espera, fallo de red o HTTP 5xx permite devolver el último valor del mismo selector con la marca de origen local. Sin valor previo se propaga el error. El SDK lo conserva en memoria hasta actualización, revocación o cierre; clone y reinicio comienzan vacíos. El Agent conserva sus credenciales en su estado local protegido. HTTP 401/403/404 o client_upgrade_required borran los valores del SDK y fallan; una respuesta exitosa inválida también falla. La revocación elimina las credenciales afectadas; snapshot elimina entradas fuera de autorización. Un cambio de configuración conserva los valores hasta comprobar el snapshot siguiente. El Agent aplica las revocaciones explícitas y las reducciones del ámbito del snapshot antes de sincronizar por HTTP, guarda ese ámbito y bloquea las lecturas locales afectadas incluso durante una caída o tras reiniciar. Una respuesta credential_not_found (HTTP 400) también elimina los valores conservados del SDK. La consulta pull directa por account_id siempre requiere una respuesta activa de la API; los snapshots de push no autorizan valores pull en caché.

- `credential.fromLocal`
- `getCredential({key, allowLocalFallback: false})` / `getCredential({accountId, allowLocalFallback: false})`

Con la escucha gestionada activa, snapshot y credential.updated consultan automáticamente la credencial actual, reemplazan el valor y llaman al manejador. Un fallo de actualización conserva el valor anterior y reintenta. El Agent también consulta tras una notificación y conserva sus datos durante fallos del servidor. Use las llamadas que requieren la API siguientes para actualizar o cambiar conexiones; un valor retenido no es una versión recién obtenida ni confirma rotaciones automáticamente.

En reposo se envía ping cada 10 segundos; unos 30 segundos sin mensajes provocan reconexión, con espera exponencial de 1–30 segundos y firma nueva. El snapshot restaura el estado actual, sin reproducir eventos históricos.



## Eventos y aplicación de credenciales

Procese snapshot inicial o de reconexión y credential.updated. El ejemplo completo maneja subscription, alternating_rotation y comandos. Implemente la validación de una conexión real, el cambio del pool y el cierre de conexiones anteriores. El marcador genera una excepción e impide confirmar antes de aplicar. Retire del estado de la aplicación las cuentas ausentes de los snapshots y procese las revocaciones.

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

En la rotación alternada, valide una conexión real, cambie el pool y cierre las conexiones anteriores antes de confirmar exactamente key, revision y account_id. Las suscripciones a cambios de credenciales no requieren confirmación. Un fallo de conexión debe impedir la confirmación.

## Comandos de aplicación

La consulta, reclamación de comandos y comunicación de resultados usan métodos SDK. Solo una reclamación aceptada ejecuta el handler. El cambio verifica versión y cuenta, aplica y confirma; el reinicio reinicia y comprueba el estado. Informe de éxito al terminar. Un fallo al informar conserva la excepción original del handler.

## Métodos habituales

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

## Solución de problemas

Los fallos HTTP, de red, autenticación y decodificación usan el tipo de error SDK con código y estado HTTP. Cierre flujos y clientes tras usarlos; los clones tienen ciclos de vida independientes. Reintente fallos transitorios en la aplicación y no registre secretos ni cabeceras de autenticación.

`PAMError`

Todos los SDK usan protocolo versión 1; Agent usa esquema de configuración versión 1. Ante client_upgrade_required (HTTP 426), verifique compatibilidad y actualice. Se toleran campos opcionales y notificaciones desconocidos; no aplique ni confirme políticas no soportadas. Los recibos se envían automáticamente y no prueban la aplicación de credenciales.

## Integración del Go Agent

La identidad usa app_id, app_secret, org_id e instance_id estable; la autorización sigue las políticas de la aplicación. Las rutas y acciones son locales: state_file conserva las contraseñas actuales, event_file añade eventos sin secretos, delivery define la salida y rules define archivos, plantillas y reload/restart o scripts fijos. Ante una actualización, el Agent obtiene y guarda la contraseña actual, reemplaza los archivos de forma atómica y ejecuta la acción; los fallos se reintentan. Use credentials[].key de get_accounts en rules; las claves de suscripción incluyen el ID de cuenta. rules vacío escribe un archivo por clave.

Las rules locales configuran archivos, JSON/EnvironmentFile o plantillas fiables y una acción systemd reload/restart o un ejecutable fijo. Los scripts reciben JSON por stdin, usan argumentos fijos y un tiempo límite, y verifican la aplicación antes de devolver éxito. Core no puede ampliar estas capacidades. Reinicie el Agent tras editar la configuración privada.

La configuración descargada ya incluye la identidad y la entrega del Agent. En rules, declare los IDs de las cuentas usadas por la aplicación, la actualización de configuración, la activación y la verificación de la conexión en ejecución. allow_account_switch permite usar la misma regla para la rotación A/B en ambos sentidos. credential_check es opcional para probar el nuevo acceso antes de cambiar archivos. Estado, eventos, Socket y conciliación de 300 segundos tienen valores predeterminados. rules vacío crea un archivo por credencial.

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

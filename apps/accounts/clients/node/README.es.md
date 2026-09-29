# JumpServer PAM Node.js SDK

Este SDK sigue las funciones del SDK Python de políticas de credenciales: obtener por cuenta autorizada o política de rotación, confirmar versiones aplicadas, escuchar eventos, procesar comandos y sincronizar Agent. URL, firma HMAC, Digest, fecha UTC, ID de solicitud y cabeceras se generan automáticamente.

## Requisitos

- Node.js 20.3+ / ws
- `demo.js`

## Configuración y ejecución

Instale el SDK fuente y configure los valores siguientes. Autorice las cuentas y vincule las políticas en Administración de aplicaciones; obtenga AK/SK e ID de organización de los materiales de acceso. Sustituya los ejemplos y proteja los secretos de despliegue. Cada réplica necesita un ID estable y único. Use un único selector: ID de cuenta o key de política.

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

## Eventos y aplicación de credenciales

Procese snapshot inicial o de reconexión y credential.updated. El ejemplo completo maneja subscription, alternating_rotation y comandos. Implemente la validación de una conexión real, el cambio del pool y el cierre de conexiones anteriores. El marcador genera una excepción e impide confirmar antes de aplicar. Retire de la caché los cuentas ausentes de los snapshots y procese las revocaciones.

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
  const credential = await client.getCredential({ key: event.credentialKey })
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
        if (mode === 'subscription' && update.accountId)
          credential = await client.getCredential({ accountId: update.accountId })
        else if (mode === 'alternating_rotation' && key)
          credential = await client.getCredential({ key })
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
- `confirmCredential({key, revision, accountId})`
- `watchCredentialEvents({signal})`
- `listApplicationCommands()`
- `reportApplicationCommandResult({commandId, status, errorCode})`
- `executeApplicationCommand(event, handler)`
- `syncAgent({credentials, deliveredCredentials, ...})`
- `clone() / close()`

## Solución de problemas

Los fallos HTTP, de red, autenticación y decodificación usan el tipo de error SDK con código y estado HTTP. Cierre flujos y clientes tras usarlos; los clones tienen ciclos de vida independientes. Reintente fallos transitorios en la aplicación y no registre secretos ni cabeceras de autenticación.

`PAMError`

Todos los SDK usan protocolo versión 1; Agent usa esquema de configuración versión 1. Ante client_upgrade_required (HTTP 426), verifique compatibilidad y actualice. Se toleran campos opcionales y notificaciones desconocidos; no aplique ni confirme políticas no soportadas. Los recibos se envían automáticamente y no prueban la aplicación de credenciales.

## Integración del Agent para Linux

La sincronización sirve para implementar Agent. Requiere identidad o source Agent e ID de configuración, y KnownRevision para versiones en caché y entregadas. La instalación Linux, entrega de archivos y API local las proporciona actualmente el Agent Python, accesible desde cualquier lenguaje.

# JumpServer PAM Node.js SDK

Ce SDK suit les fonctions du SDK Python de politiques d’identifiants : récupération par compte autorisé ou politique de rotation, confirmation des versions appliquées, événements, commandes d’application et synchronisation Agent. URL, signature HMAC, Digest, date UTC, identifiant de requête et en-têtes de protocole sont générés automatiquement.

## Prérequis

- Node.js 20.3+ / ws
- `demo.js`

## Configuration et exécution

Installez le SDK source et renseignez la configuration ci-dessous. Autorisez les comptes pour le pull dans la gestion des applications ; associez des politiques seulement si le push ou la rotation est nécessaire. Récupérez AK/SK et l’identifiant d’organisation dans les données d’accès. Remplacez les valeurs d’exemple et protégez les secrets de déploiement. Chaque réplique nécessite un identifiant stable et unique. Utilisez un seul sélecteur : identifiant de compte ou key de politique.

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

Les SDK s’installent depuis les sources de ce dépôt et ne sont pas encore publiés dans les registres publics. Remplacez /path/to/jumpserver par un chemin absolu. Exécutez l’installation Go et Node.js dans le répertoire de l’application, ou ajoutez la dépendance Java au pom.xml de l’application. Remplacez les imports locaux des exemples par les imports de paquet ci-dessous.

```bash
npm install /path/to/jumpserver/apps/accounts/clients/node
```

```javascript
const { Client } = require('@jumpserver/pam')
// ESM: import { Client } from '@jumpserver/pam'
```

## Requête et réponse

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

## Gestionnaires d’événements

Initialisez l’état local avant de démarrer l’écoute. Python et Node.js utilisent une sous-classe, Go EventHandlers et Java CredentialEventListener. Implémentez le changement réel de connexions de l’exemple. L’ancienne API reste disponible.

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

Les snapshot initiaux et de reconnexion et credential.updated récupèrent les identifiants selon le mode puis appellent le gestionnaire en série. La lecture utilise une file limitée à 128 événements, avec contre-pression si elle est pleine. Les échecs de récupération ou d’application sont retentés après 1–30 secondes de délai exponentiel, avec une nouvelle requête. Une mise à jour remplace les tentatives de la même cible ; snapshot réinitialise le périmètre, révocations et changements de configuration les annulent. Les gestionnaires doivent être idempotents. Observateurs et révocations ne sont pas retentés ; les commandes doivent être revendiquées. received signifie lu ; le SDK ne confirme jamais automatiquement une rotation. Un événement de révision antérieure n’annule pas la récupération en attente d’une révision plus récente.

`watchEvents({signal})` / `startEvents({signal})`; `stopEvents()` / `await subscription.stop()` / `await subscription.done`

watchEvents ne bloque pas la boucle d’événements ; startEvents ne garantit pas la synchronisation initiale. Un écouteur par client. Les méthodes async sont attendues en série avec AbortSignal. close annule ; attendez stop() ou done à l’extérieur. Ne pas attendre son propre done. clone retourne Client.

### Identifiants les plus récents et panne du serveur

La récupération demande d’abord l’API. Une réussite remplace les identifiants retenus ; une version ancienne ne remplace pas une nouvelle et aucune expiration temporelle n’est appliquée. Seuls un délai dépassé, une panne réseau ou HTTP 5xx permettent de retourner la dernière valeur du même sélecteur avec un indicateur local. Sans valeur précédente, l’erreur est propagée. Le SDK conserve ces valeurs en mémoire jusqu’à mise à jour, révocation ou fermeture ; clone et redémarrage commencent vides. L’Agent les conserve dans son état local protégé. HTTP 401/403/404 ou client_upgrade_required effacent les valeurs du SDK et échouent ; une réponse réussie invalide échoue aussi. Une révocation supprime les valeurs concernées, snapshot celles hors autorisation. Un changement de configuration conserve les valeurs jusqu’au snapshot suivant. L’Agent applique les révocations explicites et les réductions du périmètre du snapshot avant la synchronisation HTTP, conserve ce périmètre et bloque les lectures locales concernées même en cas de panne ou après redémarrage. Une réponse credential_not_found (HTTP 400) efface également les valeurs conservées du SDK. Le pull direct par account_id exige toujours une réponse API en direct ; les snapshots push ne valident pas les valeurs pull en cache.

- `credential.fromLocal`
- `getCredential({key, allowLocalFallback: false})` / `getCredential({accountId, allowLocalFallback: false})`

Avec l’écoute gérée, snapshot et credential.updated récupèrent automatiquement les identifiants actuels, remplacent la valeur puis appellent le gestionnaire. Un échec conserve la valeur précédente et retente. L’Agent récupère aussi après notification et conserve les données pendant une panne du serveur. Utilisez les appels exigeant l’API ci-dessous pour actualiser ou changer les connexions ; une valeur retenue n’est pas une version nouvellement récupérée et ne confirme pas automatiquement une rotation.

Au repos, ping est envoyé toutes les 10 secondes ; environ 30 secondes sans message déclenchent une reconnexion avec délai exponentiel de 1–30 secondes et nouvelle signature. Le snapshot rétablit l’état actuel sans rejouer l’historique.



## Événements et application des identifiants

Traitez snapshot initial ou de reconnexion et credential.updated. L’exemple complet gère subscription, alternating_rotation et les commandes. Implémentez le contrôle d’une connexion réelle, le changement du pool et la libération des anciennes connexions. Le code provisoire lève une exception pour empêcher toute confirmation avant application. Retirez également de l’état de l’application les comptes absents des snapshots et traitez les révocations.

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

Pour la rotation alternée, validez une connexion réelle, remplacez le pool et libérez les anciennes connexions avant de confirmer exactement key, revision et account_id. Les abonnements aux changements d’identifiants ne nécessitent aucune confirmation. Un échec du contrôle de connexion doit empêcher la confirmation.

## Commandes d’application

L’interrogation, la demande d’exécution et les résultats utilisent des méthodes SDK. Seule une demande acceptée exécute le handler. Le changement vérifie version et compte, applique puis confirme ; le redémarrage relance et contrôle l’état. Signalez le succès après la fin des opérations. Un échec du signalement conserve l’exception métier d’origine.

## Méthodes courantes

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

## Dépannage

Les erreurs HTTP, réseau, authentification et décodage utilisent le type d’erreur SDK avec code et statut HTTP. Fermez flux et clients après utilisation ; les clones ont des cycles de vie indépendants. Réessayez les pannes transitoires dans l’application et ne journalisez ni secrets ni en-têtes d’authentification.

`PAMError`

Tous les SDK utilisent le protocole version 1 ; la configuration Agent utilise le schéma version 1. Une réponse client_upgrade_required (HTTP 426) demande de vérifier la compatibilité et de mettre à jour. Les champs optionnels et notifications inconnus sont tolérés ; les politiques non prises en charge ne doivent pas être appliquées ou confirmées. Les accusés de réception sont automatiques et ne prouvent pas l’application.

## Intégration du Go Agent

L’identité utilise app_id, app_secret, org_id et un instance_id stable ; les autorisations suivent les politiques de l’application. Chemins et actions sont locaux : state_file conserve les derniers mots de passe, event_file ajoute des événements sans secrets, delivery définit la sortie et rules les fichiers, modèles et reload/restart ou scripts fixes. Après une notification, l’Agent récupère et conserve le mot de passe actuel, remplace les fichiers atomiquement puis exécute l’action ; les échecs sont retentés. Utilisez credentials[].key de get_accounts dans rules ; les clés d’abonnement incluent l’identifiant du compte. rules vide écrit un fichier par clé.

Les rules locales définissent fichiers, JSON/EnvironmentFile ou modèles fiables et une action systemd reload/restart ou un exécutable fixe. Les scripts reçoivent le JSON sur stdin, avec arguments fixes et délai limité, et vérifient l’application avant de réussir. Core ne peut pas étendre ces capacités. Redémarrez l’Agent après modification de sa configuration privée.

La configuration téléchargée contient déjà l’identité et les paramètres de livraison de l’Agent. Dans rules, indiquez les ID des comptes utilisés, la mise à jour de configuration, l’activation et la vérification de la connexion en cours. allow_account_switch permet la même règle pour la rotation A/B dans les deux sens. credential_check est facultatif pour tester le nouvel accès avant de modifier les fichiers. L’état, les événements, le Socket et la synchronisation de 300 secondes ont des valeurs par défaut. Un rules vide écrit un fichier par identifiant.

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

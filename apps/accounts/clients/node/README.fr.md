# JumpServer PAM Node.js SDK

Ce SDK suit les fonctions du SDK Python de politiques d’identifiants : récupération par compte autorisé ou politique de rotation, confirmation des versions appliquées, événements, commandes d’application et synchronisation Agent. URL, signature HMAC, Digest, date UTC, identifiant de requête et en-têtes de protocole sont générés automatiquement.

## Prérequis

- Node.js 20.3+ / ws
- `demo.js`

## Configuration et exécution

Installez le SDK source et renseignez la configuration ci-dessous. Autorisez les comptes et associez les politiques dans la gestion des applications ; récupérez AK/SK et l’identifiant d’organisation dans les données d’accès. Remplacez les valeurs d’exemple et protégez les secrets de déploiement. Chaque réplique nécessite un identifiant stable et unique. Utilisez un seul sélecteur : identifiant de compte ou key de politique.

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

## Événements et application des identifiants

Traitez snapshot initial ou de reconnexion et credential.updated. L’exemple complet gère subscription, alternating_rotation et les commandes. Implémentez le contrôle d’une connexion réelle, le changement du pool et la libération des anciennes connexions. Le code provisoire lève une exception pour empêcher toute confirmation avant application. Retirez également du cache les comptes absents des snapshots et traitez les révocations.

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

Pour la rotation alternée, validez une connexion réelle, remplacez le pool et libérez les anciennes connexions avant de confirmer exactement key, revision et account_id. Les abonnements aux changements d’identifiants ne nécessitent aucune confirmation. Un échec du contrôle de connexion doit empêcher la confirmation.

## Commandes d’application

L’interrogation, la demande d’exécution et les résultats utilisent des méthodes SDK. Seule une demande acceptée exécute le handler. Le changement vérifie version et compte, applique puis confirme ; le redémarrage relance et contrôle l’état. Signalez le succès après la fin des opérations. Un échec du signalement conserve l’exception métier d’origine.

## Méthodes courantes

- `getCredential({key})`
- `getCredential({accountId})`
- `confirmCredential({key, revision, accountId})`
- `watchCredentialEvents({signal})`
- `listApplicationCommands()`
- `reportApplicationCommandResult({commandId, status, errorCode})`
- `executeApplicationCommand(event, handler)`
- `syncAgent({credentials, deliveredCredentials, ...})`
- `clone() / close()`

## Dépannage

Les erreurs HTTP, réseau, authentification et décodage utilisent le type d’erreur SDK avec code et statut HTTP. Fermez flux et clients après utilisation ; les clones ont des cycles de vie indépendants. Réessayez les pannes transitoires dans l’application et ne journalisez ni secrets ni en-têtes d’authentification.

`PAMError`

Tous les SDK utilisent le protocole version 1 ; la configuration Agent utilise le schéma version 1. Une réponse client_upgrade_required (HTTP 426) demande de vérifier la compatibilité et de mettre à jour. Les champs optionnels et notifications inconnus sont tolérés ; les politiques non prises en charge ne doivent pas être appliquées ou confirmées. Les accusés de réception sont automatiques et ne prouvent pas l’application.

## Intégration de l’Agent Linux

La synchronisation est destinée aux implémentations Agent. Elle exige l’identité ou le source Agent et un identifiant de configuration, avec KnownRevision pour les versions en cache et distribuées. Installation Linux, distribution de fichiers et API locale sont actuellement fournies par l’Agent Python, utilisable dans tout langage.

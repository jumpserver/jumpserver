# cURL — Guide d’utilisation

Ce répertoire contient un script HTTP signé pour diagnostiquer l’ancienne API account-secret. Pour intégrer une application, utilisez le SDK Python, Go, Java ou Node.js.

## Prérequis

- Bash / cURL / OpenSSL / base64
- `demo.sh`

Le script nécessite Bash, cURL, OpenSSL et base64. Remplacez ASSET et ACCOUNT et vérifiez que la requête signée utilise exactement l’encodage envoyé par cURL.

## Configuration et exécution

Créez une application dans la gestion des applications et autorisez les comptes cibles. Configurez URL, AK/SK de l’application et identifiant de l’organisation ; remplacez toutes les valeurs d’exemple avant l’exécution.

```bash
cd apps/accounts/clients/curl
export API_URL='https://jumpserver.example.com'
export API_KEY_ID='<app-id>'
export API_KEY_SECRET='<app-secret>'
export ORG_ID='<org-id>'

bash demo.sh
```

Les exemples interrogent par défaut l’actif ubuntu_docker et le compte root. Remplacez-les par des noms réels autorisés. Exécutez les commandes depuis la racine du dépôt. La sortie contient des secrets ; ne l’envoyez pas aux journaux de l’application.

## Requête et réponse

```http
GET /api/v1/accounts/integration-applications/account-secret/?asset=ubuntu_docker&account=root
```

```json
{"id":"<app-id>","secret":"<account-secret>"}
```

Le champ id identifie l’application, et non une révision du compte. Un secret null peut refléter le réglage d’affichage des secrets du serveur. Ces exemples ne reçoivent pas d’événements, ne signalent pas de révisions appliquées et n’exécutent pas de commandes d’application.

## Dépannage

Pour 401, vérifiez AK/SK, organisation, heure de l’hôte et URL signée. Pour 403, vérifiez l’état de l’application et les autorisations des comptes. Pour 400, vérifiez sélecteurs et encodage de la requête. Ne journalisez ni secrets ni en-têtes Authorization. Les noms doivent correspondre aux ressources autorisées.

## Accès aux politiques d’identifiants

Les détails de signature et le tableau du protocole ci-dessous servent de référence pour le diagnostic. Utilisez les méthodes du SDK pour les politiques d’identifiants, ou Python Agent via des fichiers JSON, EnvironmentFile ou Unix Socket.

| HTTP | API | JSON / query |
| --- | --- | --- |
| GET | `/api/v1/accounts/credential-client/credential/` | `instance_id`, `key` / `account_id` |
| POST | `/api/v1/accounts/credential-client/confirm/` | `instance_id`, `key`, `revision`, `account_id` |
| GET | `/api/v1/accounts/credential-client/commands/` | `instance_id` |
| POST | `/api/v1/accounts/credential-client/command-result/` | `instance_id`, `command_id`, `status`, `error_code` |
| WebSocket | `/ws/accounts/credential-events/` | `instance_id` |

Signez avec HMAC-SHA256 dans l’ordre des en-têtes ci-dessous. Incluez chemin et requête encodés dans request-target, SHA-256 du corps exact dans Digest, UUID unique dans X-JMS-Request-ID, date HTTP UTC, X-JMS-Client-Version, X-JMS-Protocol-Version: 1 et X-JMS-Config-Schema-Version: 0 pour les SDK. API et WebSocket utilisent AK/SK de l’application et instance_id stable et unique ; renouvelez la signature à chaque requête ou reconnexion.

```text
(request-target) accept date digest x-jms-request-id x-jms-org
x-jms-client-version x-jms-protocol-version x-jms-config-schema-version
```

Pour la rotation alternée, validez une connexion réelle, remplacez le pool et libérez les anciennes connexions avant de confirmer exactement key, revision et account_id. Les abonnements aux changements d’identifiants ne nécessitent aucune confirmation. Un échec du contrôle de connexion doit empêcher la confirmation.

Un accusé received indique uniquement qu’un événement a été lu. Envoyez received avec event_id sur le même WebSocket avant le traitement métier ; snapshot et pong ne nécessitent aucun accusé. Réconciliez snapshot à chaque connexion ou reconnexion, traitez credential.updated et gérez révocations et changements de configuration.

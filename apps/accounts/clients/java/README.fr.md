# JumpServer PAM Java SDK

Ce SDK suit les fonctions du SDK Python de politiques d’identifiants : récupération par compte autorisé ou politique de rotation, confirmation des versions appliquées, événements, commandes d’application et synchronisation Agent. URL, signature HMAC, Digest, date UTC, identifiant de requête et en-têtes de protocole sont générés automatiquement.

## Prérequis

- JDK 11+ / Maven / Jackson
- `src/main/java/org/jumpserver/pam/Demo.java`

## Configuration et exécution

Installez le SDK source et renseignez la configuration ci-dessous. Autorisez les comptes pour le pull dans la gestion des applications ; associez des politiques seulement si le push ou la rotation est nécessaire. Récupérez AK/SK et l’identifiant d’organisation dans les données d’accès. Remplacez les valeurs d’exemple et protégez les secrets de déploiement. Chaque réplique nécessite un identifiant stable et unique. Utilisez un seul sélecteur : identifiant de compte ou key de politique.

```bash
cd apps/accounts/clients/java
export JMS_ENDPOINT='https://jumpserver.example.com'
export JMS_APP_ID='<app-id>'
export JMS_APP_SECRET='<app-secret>'
export JMS_ORG_ID='<org-id>'
export JMS_INSTANCE_ID='app-node-1'
export JMS_ACCOUNT_ID='<account-id>'

mvn package dependency:copy-dependencies
java -cp 'target/classes:target/dependency/*' org.jumpserver.pam.Demo
```

Les SDK s’installent depuis les sources de ce dépôt et ne sont pas encore publiés dans les registres publics. Remplacez /path/to/jumpserver par un chemin absolu. Exécutez l’installation Go et Node.js dans le répertoire de l’application, ou ajoutez la dépendance Java au pom.xml de l’application. Remplacez les imports locaux des exemples par les imports de paquet ci-dessous.

```bash
mvn -f /path/to/jumpserver/apps/accounts/clients/java/pom.xml install
```

```xml
<dependency>
  <groupId>org.jumpserver</groupId>
  <artifactId>jms-pam</artifactId>
  <version>1.0.0</version>
</dependency>
```

```java
import org.jumpserver.pam.Client;
```

## Requête et réponse

```java
package org.jumpserver.pam;

public final class Demo {
  public static void main(String[] args) {
    Client.Options options =
        new Client.Options(
                System.getenv("JMS_ENDPOINT"),
                System.getenv("JMS_APP_ID"),
                System.getenv("JMS_APP_SECRET"),
                System.getenv("JMS_INSTANCE_ID"))
            .orgId(System.getenv("JMS_ORG_ID"));
    try (Client client = new Client(options)) {
      Models.Credential credential =
          client.getCredentialByAccountId(System.getenv("JMS_ACCOUNT_ID"));
      // Pass credential.getAccount().getUsername() / getSecret() to the connection pool.
      System.out.println(
          "Fetched revision "
              + credential.getRevision()
              + "; implement application credential switching.");
    }
  }
}
```

## Gestionnaires d’événements

Initialisez l’état local avant de démarrer l’écoute. Python et Node.js utilisent une sous-classe, Go EventHandlers et Java CredentialEventListener. Implémentez le changement réel de connexions de l’exemple. L’ancienne API reste disponible.

```java
package org.jumpserver.pam;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.jumpserver.pam.Models.Credential;
import org.jumpserver.pam.Models.Event;

/** Replace the business hook before running. Listener methods run serially. */
public final class HooksDemo implements CredentialEventListener {
  private final Client client;
  private final Map<String, Credential> credentials = new HashMap<>();
  private final Map<String, String> modes = new HashMap<>();

  public HooksDemo(Client client) {
    this.client = client;
  }

  @Override
  public void onEvent(Event event) {
    List<Event> updates = List.of(event);
    if (event.getEvent().equals("snapshot")) {
      modes.clear();
      updates = event.getCredentials();
    }
    if (event.getEvent().equals("snapshot") || event.getEvent().equals("credential.updated"))
      for (Event update : updates) modes.put(update.getKey(), update.getCredentialMode());
    if (event.getEvent().equals("snapshot"))
      credentials.keySet().removeIf(key -> !modes.containsKey(key)); // Also release connections.
    // Use executeApplicationCommand for commands; see EventsDemo.
  }

  @Override
  public void onCredentialChanged(Credential credential) {
    applyCredential(credential);
    if ("alternating_rotation".equals(modes.get(credential.getKey())))
      client.confirmCredential(
          credential.getKey(), credential.getRevision(), credential.getAccount().getId());
    credentials.put(credential.getKey(), credential);
  }

  private void applyCredential(Credential credential) {
    throw new UnsupportedOperationException(
        "Implement connection validation, pool switching and old connection cleanup");
  }

  @Override
  public void onCredentialRevoked(Event event) {
    credentials.remove(event.getKey()); // Also release affected connections.
  }

  public static void main(String[] args) throws InterruptedException {
    Client.Options options =
        new Client.Options(
                System.getenv("JMS_ENDPOINT"),
                System.getenv("JMS_APP_ID"),
                System.getenv("JMS_APP_SECRET"),
                System.getenv("JMS_INSTANCE_ID"))
            .orgId(System.getenv("JMS_ORG_ID"));
    try (Client client = new Client(options)) {
      Thread stop = new Thread(client::close, "jms-pam-shutdown");
      Runtime.getRuntime().addShutdownHook(stop);
      try {
        client.watchEvents(new HooksDemo(client));
      } finally {
        try {
          Runtime.getRuntime().removeShutdownHook(stop);
        } catch (IllegalStateException ignored) {
        }
      }
    }
  }
}
```

Les snapshot initiaux et de reconnexion et credential.updated récupèrent les identifiants selon le mode puis appellent le gestionnaire en série. La lecture utilise une file limitée à 128 événements, avec contre-pression si elle est pleine. Les échecs de récupération ou d’application sont retentés après 1–30 secondes de délai exponentiel, avec une nouvelle requête. Une mise à jour remplace les tentatives de la même cible ; snapshot réinitialise le périmètre, révocations et changements de configuration les annulent. Les gestionnaires doivent être idempotents. Observateurs et révocations ne sont pas retentés ; les commandes doivent être revendiquées. received signifie lu ; le SDK ne confirme jamais automatiquement une rotation. Un événement de révision antérieure n’annule pas la récupération en attente d’une révision plus récente.

`watchEvents(listener)` / `startEvents(listener)`; `stop()` / `close()` / `awaitTermination()`

watchEvents attend dans le thread ; startEvents ne garantit pas la synchronisation initiale. Un écouteur par client. close attend le gestionnaire actif, qui peut fermer son propre client. awaitTermination doit être appelé à l’extérieur.

### Identifiants les plus récents et panne du serveur

La récupération demande d’abord l’API. Une réussite remplace les identifiants retenus ; une version ancienne ne remplace pas une nouvelle et aucune expiration temporelle n’est appliquée. Seuls un délai dépassé, une panne réseau ou HTTP 5xx permettent de retourner la dernière valeur du même sélecteur avec un indicateur local. Sans valeur précédente, l’erreur est propagée. Le SDK conserve ces valeurs en mémoire jusqu’à mise à jour, révocation ou fermeture ; clone et redémarrage commencent vides. L’Agent les conserve dans son état local protégé. HTTP 401/403/404 ou client_upgrade_required effacent les valeurs du SDK et échouent ; une réponse réussie invalide échoue aussi. Une révocation supprime les valeurs concernées, snapshot celles hors autorisation. Un changement de configuration conserve les valeurs jusqu’au snapshot suivant. L’Agent applique les révocations explicites et les réductions du périmètre du snapshot avant la synchronisation HTTP, conserve ce périmètre et bloque les lectures locales concernées même en cas de panne ou après redémarrage. Une réponse credential_not_found (HTTP 400) efface également les valeurs conservées du SDK. Le pull direct par account_id exige toujours une réponse API en direct ; les snapshots push ne valident pas les valeurs pull en cache.

- `credential.isFromLocal()`
- `getCredential(key, false)` / `getCredentialByAccountId(accountId, false)`

Avec l’écoute gérée, snapshot et credential.updated récupèrent automatiquement les identifiants actuels, remplacent la valeur puis appellent le gestionnaire. Un échec conserve la valeur précédente et retente. L’Agent récupère aussi après notification et conserve les données pendant une panne du serveur. Utilisez les appels exigeant l’API ci-dessous pour actualiser ou changer les connexions ; une valeur retenue n’est pas une version nouvellement récupérée et ne confirme pas automatiquement une rotation.

Au repos, ping est envoyé toutes les 10 secondes ; environ 30 secondes sans message déclenchent une reconnexion avec délai exponentiel de 1–30 secondes et nouvelle signature. Le snapshot rétablit l’état actuel sans rejouer l’historique.



## Événements et application des identifiants

Traitez snapshot initial ou de reconnexion et credential.updated. L’exemple complet gère subscription, alternating_rotation et les commandes. Implémentez le contrôle d’une connexion réelle, le changement du pool et la libération des anciennes connexions. Le code provisoire lève une exception pour empêcher toute confirmation avant application. Retirez également de l’état de l’application les comptes absents des snapshots et traitez les révocations.

```java
package org.jumpserver.pam;

import java.util.List;
import org.jumpserver.pam.Models.Credential;
import org.jumpserver.pam.Models.Event;

/** Replace the business hooks before running; unapplied credentials are never confirmed. */
public final class EventsDemo {
  private static void applyCredential(Credential credential) {
    throw new UnsupportedOperationException(
        "Implement connection validation, pool switching and old connection cleanup");
  }

  private static void restartApplication() {
    throw new UnsupportedOperationException("Implement restart and health check");
  }

  private static void handleCommand(Client client, Event event) {
    if (event.getEvent().equals("application.restart.requested")) {
      restartApplication();
      return;
    }
    if (!event.getEvent().equals("credential.switch.requested"))
      throw new IllegalArgumentException("Unsupported application command");
    Credential credential = client.getCredential(event.getKey(), false);
    if (credential.getRevision() != event.getRevision()
        || !credential.getAccount().getId().equals(event.getAccountId()))
      throw new IllegalArgumentException("Requested account version is superseded");
    applyCredential(credential);
    client.confirmCredential(
        credential.getKey(), credential.getRevision(), credential.getAccount().getId());
  }

  public static void main(String[] args) {
    Client.Options options =
        new Client.Options(
                System.getenv("JMS_ENDPOINT"),
                System.getenv("JMS_APP_ID"),
                System.getenv("JMS_APP_SECRET"),
                System.getenv("JMS_INSTANCE_ID"))
            .orgId(System.getenv("JMS_ORG_ID"));
    try (Client client = new Client(options)) {
      Thread stop = new Thread(client::close, "jms-pam-shutdown");
      Runtime.getRuntime().addShutdownHook(stop);
      try (EventStream stream = client.watchCredentialEvents()) {
        for (Event event : stream) {
          if (!event.getCommandId().isEmpty()) {
            try {
              client.executeApplicationCommand(event, command -> handleCommand(client, command));
            } catch (RuntimeException ignored) {
            }
            continue;
          }
          List<Event> updates =
              event.getEvent().equals("snapshot")
                  ? event.getCredentials()
                  : event.getEvent().equals("credential.updated") ? List.of(event) : List.of();
          // On snapshots, remove application caches absent from the new authorized scope.
          for (Event update : updates) {
            Credential credential;
            if (update.getCredentialMode().equals("subscription")
                && !update.getAccountId().isEmpty() && !update.getKey().isEmpty()) {
              String key = update.getKey();
              if (!key.endsWith(":" + update.getAccountId())) key += ":" + update.getAccountId();
              credential = client.getCredential(key, false);
            }
            else if (update.getCredentialMode().equals("alternating_rotation")
                && !update.getKey().isEmpty())
              credential = client.getCredential(update.getKey(), false);
            else continue;
            applyCredential(credential);
            if (update.getCredentialMode().equals("alternating_rotation"))
              client.confirmCredential(
                  credential.getKey(), credential.getRevision(), credential.getAccount().getId());
          }
        }
      } finally {
        try {
          Runtime.getRuntime().removeShutdownHook(stop);
        } catch (IllegalStateException ignored) {
          // The shutdown hook is already closing the client.
        }
      }
    }
  }
}
```

Pour la rotation alternée, validez une connexion réelle, remplacez le pool et libérez les anciennes connexions avant de confirmer exactement key, revision et account_id. Les abonnements aux changements d’identifiants ne nécessitent aucune confirmation. Un échec du contrôle de connexion doit empêcher la confirmation.

## Commandes d’application

L’interrogation, la demande d’exécution et les résultats utilisent des méthodes SDK. Seule une demande acceptée exécute le handler. Le changement vérifie version et compte, applique puis confirme ; le redémarrage relance et contrôle l’état. Signalez le succès après la fin des opérations. Un échec du signalement conserve l’exception métier d’origine.

## Méthodes courantes

- `getCredential(key)`
- `getCredentialByAccountId(accountId)`
- `getCredential(key, false) / getCredentialByAccountId(accountId, false)`
- `confirmCredential(key, revision, accountId)`
- `watchCredentialEvents()`
- `watchEvents(listener) / startEvents(listener)`
- `EventSubscription.stop() / close() / awaitTermination()`
- `listApplicationCommands()`
- `reportApplicationCommandResult(commandId, status, errorCode)`
- `executeApplicationCommand(event, handler)`
- `syncAgent(credentials, deliveredCredentials, configDigest, syncStatus, syncError)`
- `clone() / close()`

## Dépannage

Les erreurs HTTP, réseau, authentification et décodage utilisent le type d’erreur SDK avec code et statut HTTP. Fermez flux et clients après utilisation ; les clones ont des cycles de vie indépendants. Réessayez les pannes transitoires dans l’application et ne journalisez ni secrets ni en-têtes d’authentification.

`PAMException`

Tous les SDK utilisent le protocole version 1 ; la configuration Agent utilise le schéma version 1. Une réponse client_upgrade_required (HTTP 426) demande de vérifier la compatibilité et de mettre à jour. Les champs optionnels et notifications inconnus sont tolérés ; les politiques non prises en charge ne doivent pas être appliquées ou confirmées. Les accusés de réception sont automatiques et ne prouvent pas l’application.

## Intégration du Go Agent

L’identité utilise app_id, app_secret, org_id et un instance_id stable ; les autorisations suivent les politiques de l’application. Chemins et actions sont locaux : state_file conserve les derniers mots de passe, event_file ajoute des événements sans secrets, delivery définit la sortie et rules les fichiers, modèles et reload/restart ou scripts fixes. Après une notification, l’Agent récupère et conserve le mot de passe actuel, remplace les fichiers atomiquement puis exécute l’action ; les échecs sont retentés. Utilisez credentials[].key de get_accounts dans rules ; les clés d’abonnement incluent l’identifiant du compte. rules vide écrit un fichier par clé.

Les rules locales définissent fichiers, JSON/EnvironmentFile ou modèles fiables et une action systemd reload/restart ou un exécutable fixe. Les scripts reçoivent le JSON sur stdin, avec arguments fixes et délai limité, et vérifient l’application avant de réussir. Core ne peut pas étendre ces capacités. Redémarrez l’Agent après modification de sa configuration privée.

L’identité utilise app_id, app_secret, org_id et un instance_id stable ; les autorisations suivent les politiques de l’application. Chemins et actions sont locaux : state_file conserve les derniers mots de passe, event_file ajoute des événements sans secrets, delivery définit la sortie et rules les fichiers, modèles et reload/restart ou scripts fixes. Après une notification, l’Agent récupère et conserve le mot de passe actuel, remplace les fichiers atomiquement puis exécute l’action ; les échecs sont retentés. Utilisez credentials[].key de get_accounts dans rules ; les clés d’abonnement incluent l’identifiant du compte. rules vide écrit un fichier par clé.

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

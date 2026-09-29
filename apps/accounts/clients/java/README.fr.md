# JumpServer PAM Java SDK

Ce SDK suit les fonctions du SDK Python de politiques d’identifiants : récupération par compte autorisé ou politique de rotation, confirmation des versions appliquées, événements, commandes d’application et synchronisation Agent. URL, signature HMAC, Digest, date UTC, identifiant de requête et en-têtes de protocole sont générés automatiquement.

## Prérequis

- JDK 11+ / Maven / Jackson
- `src/main/java/org/jumpserver/pam/Demo.java`

## Configuration et exécution

Installez le SDK source et renseignez la configuration ci-dessous. Autorisez les comptes et associez les politiques dans la gestion des applications ; récupérez AK/SK et l’identifiant d’organisation dans les données d’accès. Remplacez les valeurs d’exemple et protégez les secrets de déploiement. Chaque réplique nécessite un identifiant stable et unique. Utilisez un seul sélecteur : identifiant de compte ou key de politique.

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

## Événements et application des identifiants

Traitez snapshot initial ou de reconnexion et credential.updated. L’exemple complet gère subscription, alternating_rotation et les commandes. Implémentez le contrôle d’une connexion réelle, le changement du pool et la libération des anciennes connexions. Le code provisoire lève une exception pour empêcher toute confirmation avant application. Retirez également du cache les comptes absents des snapshots et traitez les révocations.

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
    Credential credential = client.getCredential(event.getKey());
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
                && !update.getAccountId().isEmpty())
              credential = client.getCredentialByAccountId(update.getAccountId());
            else if (update.getCredentialMode().equals("alternating_rotation")
                && !update.getKey().isEmpty()) credential = client.getCredential(update.getKey());
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
- `confirmCredential(key, revision, accountId)`
- `watchCredentialEvents()`
- `listApplicationCommands()`
- `reportApplicationCommandResult(commandId, status, errorCode)`
- `executeApplicationCommand(event, handler)`
- `syncAgent(credentials, deliveredCredentials, configDigest, syncStatus, syncError)`
- `clone() / close()`

## Dépannage

Les erreurs HTTP, réseau, authentification et décodage utilisent le type d’erreur SDK avec code et statut HTTP. Fermez flux et clients après utilisation ; les clones ont des cycles de vie indépendants. Réessayez les pannes transitoires dans l’application et ne journalisez ni secrets ni en-têtes d’authentification.

`PAMException`

Tous les SDK utilisent le protocole version 1 ; la configuration Agent utilise le schéma version 1. Une réponse client_upgrade_required (HTTP 426) demande de vérifier la compatibilité et de mettre à jour. Les champs optionnels et notifications inconnus sont tolérés ; les politiques non prises en charge ne doivent pas être appliquées ou confirmées. Les accusés de réception sont automatiques et ne prouvent pas l’application.

## Intégration de l’Agent Linux

La synchronisation est destinée aux implémentations Agent. Elle exige l’identité ou le source Agent et un identifiant de configuration, avec KnownRevision pour les versions en cache et distribuées. Installation Linux, distribution de fichiers et API locale sont actuellement fournies par l’Agent Python, utilisable dans tout langage.

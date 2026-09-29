# JumpServer PAM Java SDK

Este SDK acompanha o SDK Python de políticas de credenciais: consulta por conta autorizada ou política de rotação, confirmação de versões aplicadas, eventos, comandos e sincronização Agent. URL, assinatura HMAC, Digest, data UTC, ID de requisição e cabeçalhos são gerados automaticamente.

## Requisitos

- JDK 11+ / Maven / Jackson
- `src/main/java/org/jumpserver/pam/Demo.java`

## Configurar e executar

Instale o SDK fonte e configure os valores abaixo. Autorize contas e vincule políticas em Gerenciamento de aplicações; obtenha AK/SK e ID da organização nos materiais de acesso. Substitua os exemplos e proteja os segredos de implantação. Cada réplica precisa de um ID estável e único. Use um só seletor: ID da conta ou key da política.

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

Os SDKs são instalados a partir deste repositório e ainda não foram publicados em registros públicos. Substitua /path/to/jumpserver por um caminho absoluto. Execute a instalação Go e Node.js no diretório da aplicação ou adicione a dependência Java ao pom.xml da aplicação. Substitua as importações locais dos exemplos pelas importações de pacote abaixo.

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

## Requisição e resposta

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

## Eventos e aplicação de credenciais

Processe snapshot inicial ou de reconexão e credential.updated. O exemplo completo trata subscription, alternating_rotation e comandos. Implemente verificação de conexão real, troca do pool e liberação das conexões antigas. O marcador lança uma exceção e impede confirmar antes de aplicar. Remova do cache contas ausentes dos snapshots e trate revogações.

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

Na rotação alternada, valide uma conexão real, troque o pool e libere conexões antigas antes de confirmar exatamente key, revision e account_id. Assinaturas de alterações de credenciais não exigem confirmação. Falhas na verificação de conexão devem impedir a confirmação.

## Comandos de aplicação

Consulta, solicitação de execução e resultados usam métodos SDK. Apenas uma solicitação aceita executa o handler. A troca verifica versão e conta, aplica e confirma; o reinício reinicia e verifica a saúde. Informe sucesso ao concluir. Falhas no relatório preservam a exceção original do handler.

## Métodos comuns

- `getCredential(key)`
- `getCredentialByAccountId(accountId)`
- `confirmCredential(key, revision, accountId)`
- `watchCredentialEvents()`
- `listApplicationCommands()`
- `reportApplicationCommandResult(commandId, status, errorCode)`
- `executeApplicationCommand(event, handler)`
- `syncAgent(credentials, deliveredCredentials, configDigest, syncStatus, syncError)`
- `clone() / close()`

## Solução de problemas

Falhas HTTP, rede, autenticação e decodificação usam o tipo de erro SDK com código e estado HTTP. Feche fluxos e clientes após usar; clones têm ciclos de vida independentes. Repita falhas transitórias na aplicação e não registre segredos nem cabeçalhos de autenticação.

`PAMException`

Todos os SDKs usam protocolo versão 1; Agent usa esquema de configuração versão 1. Em client_upgrade_required (HTTP 426), verifique compatibilidade e atualize. Campos opcionais e notificações desconhecidos são tolerados; não aplique nem confirme políticas não suportadas. Os recibos são automáticos e não provam aplicação de credenciais.

## Integração com o Agent Linux

A sincronização serve para implementar Agent. Exige identidade ou source Agent e ID de configuração, com KnownRevision para versões em cache e entregues. Instalação Linux, entrega de arquivos e API local são atualmente fornecidas pelo Agent Python, acessível de qualquer linguagem.

# JumpServer PAM Java SDK

本 SDK 与 Python 凭据策略 SDK 对齐：获取授权账号或轮换策略凭据、确认生效版本、监听事件、处理应用指令、同步 Agent 状态。请求 URL、HMAC 签名、Digest、UTC 时间、请求 ID 和协议头均由客户端自动生成。

## 环境要求

- JDK 11+ / Maven / Jackson
- `src/main/java/org/jumpserver/pam/Demo.java`

## 配置与运行

安装源码 SDK，填写下方配置。在应用管理中授权账号并绑定策略，从应用接入材料获取应用 AK/SK 和组织 ID。替换占位符，将身份材料保存在部署密钥中，每个副本使用稳定、唯一的实例 ID。取密只能选择账号 ID 或策略 key 中的一种。

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

SDK 当前从本仓库源码安装，尚未发布到公共包仓库。将 /path/to/jumpserver 替换为绝对路径；Go 和 Node.js 安装命令在应用目录执行，Java 依赖添加到应用 pom.xml。仓库运行示例的本地导入在应用中应替换为下方包导入。

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

## 请求与响应

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

## 事件与凭据生效

处理首次/重连 snapshot 和 credential.updated。下方完整事件示例分别处理 subscription、alternating_rotation 及应用指令。替换凭据应用函数：验证真实连接、切换连接池并释放旧连接。占位函数会抛出异常，防止确认尚未应用的版本；应用缓存还须按快照移除已撤销账号，并处理撤销事件。

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

交替轮换需要先验证真实连接、切换应用连接池并释放旧连接，再确认准确的 key、revision 和 account_id。凭据变更订阅无需确认，连接验证失败时不得确认。

## 应用指令

轮询、指令认领和结果上报均通过 SDK 方法完成，只有认领成功才执行处理函数。切换指令校验请求的版本与账号、应用凭据后再确认；重启指令须完成重启及健康检查。工作完成后才报告成功，失败上报不会掩盖原始业务异常。

## 常用方法

- `getCredential(key)`
- `getCredentialByAccountId(accountId)`
- `confirmCredential(key, revision, accountId)`
- `watchCredentialEvents()`
- `listApplicationCommands()`
- `reportApplicationCommandResult(commandId, status, errorCode)`
- `executeApplicationCommand(event, handler)`
- `syncAgent(credentials, deliveredCredentials, configDigest, syncStatus, syncError)`
- `clone() / close()`

## 排查问题

HTTP、网络、认证和响应解码错误使用 SDK 异常或错误类型，包含错误码及 HTTP 状态。使用完成后关闭事件流与客户端，克隆客户端具有独立生命周期。在业务边界重试临时故障，不记录密码或认证请求头。

`PAMException`

各 SDK 使用版本 1 协议，Agent 配置格式为版本 1。收到 client_upgrade_required（HTTP 426）时检查兼容性并升级。允许未知可选字段及通知事件，未实现的策略类型不得应用或确认。事件接收回执由 SDK 自动发送，不能作为凭据已经生效的证明。

## Linux Agent 接入

Agent 同步方法供 Agent 实现复用，需要 Agent 身份或 source 及配置 ID，使用 KnownRevision 上报缓存与交付版本。目前 Linux 安装、文件交付和本地 API 由 Python Agent 提供，各编程语言的应用均可接入该 Agent。

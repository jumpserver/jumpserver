# JumpServer PAM Java SDK

SDK này theo chức năng của SDK chính sách thông tin xác thực Python: lấy theo tài khoản được phép hoặc chính sách luân phiên, xác nhận phiên bản áp dụng, theo dõi sự kiện, xử lý lệnh và đồng bộ Agent. URL, chữ ký HMAC, Digest, thời gian UTC, ID yêu cầu và tiêu đề được tạo tự động.

## Yêu cầu môi trường

- JDK 11+ / Maven / Jackson
- `src/main/java/org/jumpserver/pam/Demo.java`

## Cấu hình và chạy

Cài SDK nguồn và cấu hình bên dưới. Cấp quyền tài khoản cho pull trong quản lý ứng dụng; chỉ gắn chính sách khi cần push hoặc luân phiên thông tin xác thực. Lấy AK/SK và ID tổ chức từ tài liệu kết nối. Thay các giá trị mẫu và bảo vệ bí mật triển khai. Mỗi bản sao cần ID ổn định và duy nhất. Chỉ dùng một bộ chọn: ID tài khoản hoặc key chính sách.

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

Các SDK hiện được cài từ mã nguồn kho này và chưa được phát hành lên kho gói công khai. Thay /path/to/jumpserver bằng đường dẫn tuyệt đối. Chạy lệnh cài Go và Node.js trong thư mục ứng dụng hoặc thêm phụ thuộc Java vào pom.xml của ứng dụng. Thay lệnh nhập cục bộ trong ví dụ bằng lệnh nhập gói dưới đây.

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

## Yêu cầu và phản hồi

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

## Hàm xử lý sự kiện

Khởi tạo trạng thái cục bộ trước khi lắng nghe. Python và Node.js dùng lớp con, Go dùng EventHandlers, Java dùng CredentialEventListener. Hãy triển khai việc chuyển kết nối thật trong ví dụ. API cũ vẫn được giữ lại.

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

snapshot ban đầu, khi kết nối lại và credential.updated lấy thông tin theo chế độ rồi gọi hàm xử lý tuần tự. Bộ đọc dùng hàng đợi giới hạn 128 sự kiện; khi đầy sẽ tạo áp lực ngược. Lỗi lấy hoặc áp dụng được thử lại với thời gian chờ tăng theo hàm mũ 1–30 giây, mỗi lần đều lấy lại. Sự kiện mới thay thế lần thử của cùng mục tiêu; snapshot đặt lại phạm vi, thu hồi và thay đổi cấu hình hủy các lần thử. Hàm xử lý phải gọi lặp lại an toàn. Hàm quan sát và thu hồi không tự thử lại; lệnh phải được nhận quyền thực thi. received chỉ nghĩa là đã đọc; SDK không tự xác nhận luân chuyển. Sự kiện phiên bản cũ không hủy lần lấy lại đang chờ cho phiên bản mới hơn.

`watchEvents(listener)` / `startEvents(listener)`; `stop()` / `close()` / `awaitTermination()`

watchEvents chờ trong luồng gọi; startEvents không đảm bảo đồng bộ ban đầu. Một bộ lắng nghe mỗi client. close chờ hàm xử lý và có thể gọi từ hàm đó. awaitTermination phải gọi bên ngoài.

### Thông tin xác thực mới nhất và lỗi máy chủ

Luôn gọi API trước. Kết quả thành công thay thế giá trị đang giữ; phiên bản cũ không ghi đè bản mới và không có thời hạn hết hiệu lực theo thời gian. Chỉ hết thời gian chờ, lỗi mạng hoặc HTTP 5xx mới trả về giá trị thành công gần nhất của cùng bộ chọn với cờ nguồn cục bộ. Chưa có giá trị thì báo lỗi gốc. SDK giữ trong bộ nhớ client đến khi cập nhật, thu hồi hoặc đóng; clone và khởi động lại bắt đầu trống. Agent dùng trạng thái cục bộ được bảo vệ sẵn có. HTTP 401/403/404 hoặc client_upgrade_required xóa giá trị SDK rồi báo lỗi; phản hồi thành công không hợp lệ cũng báo lỗi. Thu hồi xóa mục liên quan, snapshot xóa mục ngoài quyền. Thay đổi cấu hình giữ giá trị đến khi kiểm tra snapshot tiếp theo. Agent áp dụng thu hồi rõ ràng và thu hẹp phạm vi snapshot trước khi đồng bộ HTTP, lưu phạm vi đó và chặn các lần lấy cục bộ liên quan ngay cả khi máy chủ lỗi hoặc sau khi khởi động lại. Phản hồi credential_not_found (HTTP 400) cũng xóa giá trị SDK được giữ lại. Pull trực tiếp bằng account_id luôn cần phản hồi API trực tiếp; snapshot push không xác nhận quyền dùng giá trị pull đã lưu.

- `credential.isFromLocal()`
- `getCredential(key, false)` / `getCredentialByAccountId(accountId, false)`

Khi bật lắng nghe được quản lý, snapshot và credential.updated tự lấy dữ liệu, thay thế giá trị và gọi hàm nghiệp vụ. Lỗi cập nhật giữ bản trước và thử lại. Agent cũng lấy lại theo thông báo, giữ dữ liệu khi máy chủ lỗi. Dùng lời gọi bắt buộc API bên dưới để cập nhật hay chuyển kết nối; giá trị đang giữ không phải phiên bản vừa lấy và không tự xác nhận luân chuyển.

Khi nhàn rỗi gửi ping mỗi 10 giây; khoảng 30 giây không có tin nhắn sẽ kết nối lại, chờ tăng theo hàm mũ 1–30 giây và ký mới. snapshot khôi phục trạng thái hiện tại, không phát lại lịch sử.



## Sự kiện và áp dụng thông tin xác thực

Xử lý snapshot đầu tiên/kết nối lại và credential.updated. Ví dụ đầy đủ xử lý subscription, alternating_rotation và lệnh. Triển khai kiểm tra kết nối thực, chuyển nhóm kết nối và giải phóng kết nối cũ. Hàm mẫu ném lỗi để ngăn xác nhận trước khi áp dụng. Xóa khỏi trạng thái ứng dụng các tài khoản không còn trong snapshot và xử lý thu hồi.

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

Với luân phiên hai tài khoản, xác minh kết nối thật, chuyển nhóm kết nối và giải phóng kết nối cũ trước khi xác nhận đúng key, revision và account_id. Đăng ký thay đổi thông tin xác thực không cần xác nhận. Không xác nhận khi kiểm tra kết nối thất bại.

## Lệnh ứng dụng

Thăm dò, nhận quyền thực thi và báo cáo kết quả dùng phương thức SDK. Chỉ nhận quyền thành công mới chạy hàm xử lý. Chuyển đổi kiểm tra phiên bản và tài khoản, áp dụng rồi xác nhận; khởi động lại phải kiểm tra tình trạng sau khởi động. Chỉ báo thành công khi hoàn tất. Lỗi báo cáo không thay thế lỗi nghiệp vụ gốc.

## Phương thức thông dụng

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

## Khắc phục sự cố

Lỗi HTTP, mạng, xác thực và giải mã dùng kiểu lỗi SDK với mã và trạng thái HTTP. Đóng luồng và máy khách sau khi dùng; bản sao có vòng đời độc lập. Thử lại lỗi tạm thời ở tầng ứng dụng và không ghi bí mật hay tiêu đề xác thực vào nhật ký.

`PAMException`

Mọi SDK dùng giao thức phiên bản 1; Agent dùng lược đồ cấu hình phiên bản 1. Khi nhận client_upgrade_required (HTTP 426), kiểm tra tương thích và nâng cấp. Cho phép trường tùy chọn và thông báo chưa biết; không áp dụng hay xác nhận chính sách chưa hỗ trợ. Biên nhận được gửi tự động và không chứng minh đã áp dụng thông tin xác thực.

## Tích hợp Go Agent

Danh tính dùng app_id, app_secret, org_id và instance_id ổn định; quyền theo chính sách gắn với ứng dụng. Đường dẫn và thao tác dịch vụ đều ở máy cục bộ: state_file giữ mật khẩu mới nhất, event_file ghi sự kiện không có bí mật, delivery chọn đầu ra mặc định, rules đặt tệp, mẫu và reload/restart hoặc tập lệnh cố định. Khi nhận thông báo, Agent lấy và lưu mật khẩu hiện tại, thay tệp nguyên tử rồi chạy thao tác; lỗi sẽ được thử lại. Dùng credentials[].key từ get_accounts cho rules; key đăng ký chứa ID tài khoản. rules rỗng ghi một tệp cho mỗi key.

rules cục bộ cấu hình tệp, JSON/EnvironmentFile hoặc mẫu tin cậy cùng systemd reload/restart hoặc chương trình cố định. Script nhận JSON qua stdin, dùng đối số cố định và giới hạn thời gian, rồi kiểm tra ứng dụng trước khi báo thành công. Core không được mở rộng quyền này. Khởi động lại Agent sau khi sửa cấu hình riêng tư.

Danh tính dùng app_id, app_secret, org_id và instance_id ổn định; quyền theo chính sách gắn với ứng dụng. Đường dẫn và thao tác dịch vụ đều ở máy cục bộ: state_file giữ mật khẩu mới nhất, event_file ghi sự kiện không có bí mật, delivery chọn đầu ra mặc định, rules đặt tệp, mẫu và reload/restart hoặc tập lệnh cố định. Khi nhận thông báo, Agent lấy và lưu mật khẩu hiện tại, thay tệp nguyên tử rồi chạy thao tác; lỗi sẽ được thử lại. Dùng credentials[].key từ get_accounts cho rules; key đăng ký chứa ID tài khoản. rules rỗng ghi một tệp cho mỗi key.

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

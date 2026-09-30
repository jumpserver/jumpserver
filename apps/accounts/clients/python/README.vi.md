# JumpServer PAM Python SDK / Agent

Python 3.9+ cung cấp SDK chính sách thông tin xác thực. Go jms-pam-agent phân phối qua tệp cục bộ, hành động cố định hoặc Socket cục bộ mà không cần Python. Chạy trực tiếp trên Linux, macOS và Windows; cài đặt systemd tích hợp chỉ dành cho Linux.

<!-- agent-doc:start -->

## Tích hợp Go Agent

Chuẩn bị Linux có systemd và người dùng ứng dụng. Tải jms_pam_agent.json từ trình hướng dẫn, biên dịch hoặc nhận binary Go rồi cài với ID ổn định và duy nhất. Cấu hình cục bộ là /etc/jms-pam-agent/agent.json, tên dịch vụ cố định là jms-pam-agent.

```bash
cd apps/accounts/clients/go
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
chmod 0600 ./jms_pam_agent.json
sudo /usr/local/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

Trình cài đặt tích hợp cần Linux và root. Trên macOS, Linux không có root hoặc Windows, chọn JSON hoặc Socket trong trình hướng dẫn và chạy init-local cùng run --local --config. Chỉ khởi tạo một lần rồi dùng lại cấu hình cục bộ riêng tư; chế độ chạy trực tiếp không thực hiện thao tác systemd.

`/etc/jms-pam-agent/agent.json`: `0600`; `state_file`, `event_file`, `delivery.delivery_root`, `delivery.socket_path`.

- JSON: `/opt/jumpserver-pam/credentials/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<credential-key>.env`
- Unix Socket: `/run/jms-pam-agent/agent.sock`

JSON giao tệp, EnvironmentFile dùng dịch vụ systemd cố định, Unix Socket cung cấp API cục bộ. Agent ghi phiên bản đã giao sau thành công; ứng dụng ghi phiên bản đã áp dụng sau kiểm tra và sử dụng. Socket thuộc người dùng ứng dụng với quyền 0600; gửi yêu cầu bằng người dùng đó.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<credential-key>.env
```

Unit systemd phải tham chiếu EnvironmentFile. Chỉ dùng reload khi ứng dụng đọc lại tệp; reload không đưa biến môi trường mới vào tiến trình đang chạy. Đường dẫn, người dùng, dịch vụ và thao tác được cố định khi cài; mở rộng quyền cần cài lại.

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


### API cục bộ và xác nhận

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

Với luân phiên hai tài khoản, xác minh kết nối thật, chuyển nhóm kết nối và giải phóng kết nối cũ trước khi xác nhận đúng key, revision và account_id. Đăng ký thay đổi thông tin xác thực không cần xác nhận. Không xác nhận khi kiểm tra kết nối thất bại.

```bash
/usr/local/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jms-pam-agent/agent.sock'
```

Chỉ luân phiên cần confirm. Xác nhận cục bộ được lưu bền vững trước; confirmed nghĩa là Core đã nhận, pending nghĩa là sẽ thử lại. Không xác nhận chỉ vì ghi tệp hoặc khởi động lại dịch vụ thành công.

### Khắc phục sự cố

```bash
sudo systemctl start jms-pam-agent
sudo systemctl status jms-pam-agent --no-pager
sudo journalctl -u jms-pam-agent -n 100 --no-pager
sudo systemctl restart jms-pam-agent
```

Agent đồng bộ lúc khởi động, theo sự kiện liên quan và mỗi 300 giây. Lỗi mạng giữ thông tin xác thực mới nhất đã lấy và được cấp quyền. Khi danh tính/quyền bị từ chối, chặn lấy qua Socket; đồng bộ có chữ ký thành công sẽ khôi phục. Tệp đã giao vẫn được giữ. SIGINT/SIGTERM đóng dịch vụ, kết nối và luồng đọc.

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Tích hợp Python SDK

Tạo và gắn chính sách, cấp quyền tài khoản tài sản, tải jms_pam_config.py từ trình hướng dẫn của ứng dụng. Cần Python 3.9+. Chạy lệnh cài kho mã bên dưới hoặc python3 -m pip install . trong thư mục SDK đã giải nén.

```bash
python3 -m pip install ./apps/accounts/clients/python
```

Đặt jms_pam_config.py nơi ứng dụng có thể nhập. client_options chứa danh tính ứng dụng: không đưa vào kho mã hay nhật ký. Mỗi bản sao có instance_id ổn định, duy nhất. get_credential nhận đúng một bộ chọn: account_id cho tài khoản hoặc key cho chính sách luân phiên.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


with Client(instance_id=instance_id, **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### Sự kiện và áp dụng thông tin xác thực

Xử lý snapshot ban đầu/khi kết nối lại và credential.updated. Ví dụ tách subscription với alternating_rotation. Triển khai apply_credential để xác minh kết nối thật, chuyển nhóm kết nối và giải phóng kết nối cũ. Hàm giữ chỗ phát sinh lỗi để ngăn xác nhận thông tin chưa áp dụng.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def apply_credential(credential):
    raise NotImplementedError('Hãy triển khai và xác minh việc chuyển thông tin xác thực của ứng dụng')


with Client(instance_id=instance_id, **client_options) as client:
    for event in client.watch_credential_events():
        if event.get("event") == "snapshot":
            updates = event.get("credentials", [])
        elif event.get("event") == "credential.updated":
            updates = [event]
        else:
            continue
        for update in updates:
            mode = update.get("credential_mode")
            key = update.get("credential_key") or update.get("key")
            account_id = update.get("account_id")
            if mode == "subscription" and account_id and key:
                policy_key = key if key.endswith(f":{account_id}") else f"{key}:{account_id}"
                credential = client.get_credential(key=policy_key, allow_local_fallback=False)
            elif mode == "alternating_rotation" and key:
                credential = client.get_credential(key=key, allow_local_fallback=False)
            else:
                continue
            apply_credential(credential)
            if mode == "alternating_rotation":
                client.confirm_credential(
                    key=credential.key,
                    revision=credential.revision,
                    account_id=credential.account.id,
                )
```

Với luân phiên hai tài khoản, xác minh kết nối thật, chuyển nhóm kết nối và giải phóng kết nối cũ trước khi xác nhận đúng key, revision và account_id. Đăng ký thay đổi thông tin xác thực không cần xác nhận. Không xác nhận khi kiểm tra kết nối thất bại.

SDK tự động cố gắng gửi biên nhận received trước khi trả về sự kiện nghiệp vụ. Ứng dụng không cần gửi thêm. Biên nhận chỉ cho biết đã đọc sự kiện, không có nghĩa là đã áp dụng thông tin xác thực và không thay thế xác nhận. Đối chiếu snapshot ban đầu và khi kết nối lại; snapshot và pong không cần biên nhận.

## Hàm xử lý sự kiện

Khởi tạo trạng thái cục bộ trước khi lắng nghe. Python và Node.js dùng lớp con, Go dùng EventHandlers, Java dùng CredentialEventListener. Hãy triển khai việc chuyển kết nối thật trong ví dụ. API cũ vẫn được giữ lại.

```python
"""Subscription example using subclass hooks; demo.py retains the iterator API."""

from jms_pam import Client
from jms_pam_config import client_options


class MyClient(Client):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.credentials = {}

    def on_event(self, event):
        if event.get("event") == "snapshot":
            authorized_keys = {item["key"] for item in event.get("credentials", [])}
            for key in self.credentials.keys() - authorized_keys:
                # Also release this key's application connections.
                del self.credentials[key]

    def on_credential_changed(self, credential):
        # Validate and switch application connections using credential.asset and
        # credential.account. The handler must be safe to repeat on retry/reconnect.
        # Never log credential.account.secret or authentication headers.
        raise NotImplementedError("Implement the application connection update first")
        # Save only after the application has successfully switched connections:
        # self.credentials[credential.key] = credential

    def on_credential_revoked(self, event):
        self.credentials.pop(event.get("credential_key"), None)
        # Also release the affected application connections.


with MyClient(instance_id="order-service-node-1", **client_options) as client:
    client.watch_events()
```

snapshot ban đầu, khi kết nối lại và credential.updated lấy thông tin theo chế độ rồi gọi hàm xử lý tuần tự. Bộ đọc dùng hàng đợi giới hạn 128 sự kiện; khi đầy sẽ tạo áp lực ngược. Lỗi lấy hoặc áp dụng được thử lại với thời gian chờ tăng theo hàm mũ 1–30 giây, mỗi lần đều lấy lại. Sự kiện mới thay thế lần thử của cùng mục tiêu; snapshot đặt lại phạm vi, thu hồi và thay đổi cấu hình hủy các lần thử. Hàm xử lý phải gọi lặp lại an toàn. Hàm quan sát và thu hồi không tự thử lại; lệnh phải được nhận quyền thực thi. received chỉ nghĩa là đã đọc; SDK không tự xác nhận luân chuyển. Sự kiện phiên bản cũ không hủy lần lấy lại đang chờ cho phiên bản mới hơn.

`watch_events(stop_event=...)` / `start_events(stop_event=...)`; `stop_events()` / `close()`

watch_events chờ dừng; start_events không đảm bảo đồng bộ ban đầu. Chờ ứng dụng sẵn sàng. Mỗi client chỉ có một bộ lắng nghe. stop_events và close chờ hàm xử lý; hàm có thể dừng client của mình. clone khởi tạo lại lớp con.

### Thông tin xác thực mới nhất và lỗi máy chủ

Luôn gọi API trước. Kết quả thành công thay thế giá trị đang giữ; phiên bản cũ không ghi đè bản mới và không có thời hạn hết hiệu lực theo thời gian. Chỉ hết thời gian chờ, lỗi mạng hoặc HTTP 5xx mới trả về giá trị thành công gần nhất của cùng bộ chọn với cờ nguồn cục bộ. Chưa có giá trị thì báo lỗi gốc. SDK giữ trong bộ nhớ client đến khi cập nhật, thu hồi hoặc đóng; clone và khởi động lại bắt đầu trống. Agent dùng trạng thái cục bộ được bảo vệ sẵn có. HTTP 401/403/404 hoặc client_upgrade_required xóa giá trị SDK rồi báo lỗi; phản hồi thành công không hợp lệ cũng báo lỗi. Thu hồi xóa mục liên quan, snapshot xóa mục ngoài quyền. Thay đổi cấu hình giữ giá trị đến khi kiểm tra snapshot tiếp theo. Agent áp dụng thu hồi rõ ràng và thu hẹp phạm vi snapshot trước khi đồng bộ HTTP, lưu phạm vi đó và chặn các lần lấy cục bộ liên quan ngay cả khi máy chủ lỗi hoặc sau khi khởi động lại. Phản hồi credential_not_found (HTTP 400) cũng xóa giá trị SDK được giữ lại. Pull trực tiếp bằng account_id luôn cần phản hồi API trực tiếp; snapshot push không xác nhận quyền dùng giá trị pull đã lưu.

- `credential.from_local`
- `get_credential(key=..., allow_local_fallback=False)` / `get_credential(account_id=..., allow_local_fallback=False)`

Khi bật lắng nghe được quản lý, snapshot và credential.updated tự lấy dữ liệu, thay thế giá trị và gọi hàm nghiệp vụ. Lỗi cập nhật giữ bản trước và thử lại. Agent cũng lấy lại theo thông báo, giữ dữ liệu khi máy chủ lỗi. Dùng lời gọi bắt buộc API bên dưới để cập nhật hay chuyển kết nối; giá trị đang giữ không phải phiên bản vừa lấy và không tự xác nhận luân chuyển.

Khi nhàn rỗi gửi ping mỗi 10 giây; khoảng 30 giây không có tin nhắn sẽ kết nối lại, chờ tăng theo hàm mũ 1–30 giây và ký mới. snapshot khôi phục trạng thái hiện tại, không phát lại lịch sử.



### Lệnh ứng dụng

Dùng list_application_commands để lấy yêu cầu chờ và execute_application_command(event, handler) để nhận quyền thực thi. Chỉ chạy khi accepted là true. Hàm chuyển kiểm tra tài khoản/phiên bản yêu cầu, áp dụng và xác nhận; hàm khởi động lại phải kiểm tra sức khỏe trước khi báo thành công. Lỗi báo cáo thất bại không che lỗi xử lý ban đầu.

### Phương thức thông dụng

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `watch_events(stop_event=...)` / `start_events(stop_event=...)` / `stop_events()`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

with hoặc close đóng phiên HTTP và luồng sự kiện; clone tạo phiên độc lập. Lỗi HTTP, mạng, xác thực và phân tích tạo PAMError có code, status_code, detail, original_error. Thử lại lỗi tạm thời tại ranh giới ứng dụng, xử lý rõ việc từ chối quyền và không ghi thông tin xác thực.

Mã mới dùng phương thức từ khóa snake_case và thuộc tính dataclass. API đối tượng yêu cầu credential.v1 cũ vẫn có với DeprecationWarning. SDK và Agent dùng giao thức phiên bản 1; sync_agent nhận KnownRevision cho phiên bản được giữ lại và đã giao.

<!-- sdk-doc:end -->

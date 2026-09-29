# JumpServer PAM Python SDK / Agent

Python 3.9+ cung cấp SDK chính sách thông tin xác thực và Linux Agent. SDK dùng AK/SK ứng dụng; Agent giao thông tin xác thực tại máy cục bộ để ứng dụng ngôn ngữ khác cũng sử dụng được.

<!-- agent-doc:start -->

## Tích hợp Linux Agent

Chuẩn bị máy Linux có systemd, Python 3.9+ và người dùng ứng dụng. Gắn ứng dụng với chính sách và cấp quyền tài khoản; luân phiên cần cả hai tài khoản. Trong trình hướng dẫn, chọn Agent, người dùng chạy, đường dẫn cài và cách giao, rồi tải jms_pam_agent.json. Cài thư mục SDK đã tải và chạy lệnh theo đường dẫn mặc định bên dưới. Mỗi bản sao cần ID ổn định, duy nhất.

```bash
sudo python3 -m venv /opt/jumpserver-pam/venv
sudo /opt/jumpserver-pam/venv/bin/python -m pip install '<sdk-directory>'
sudo /opt/jumpserver-pam/venv/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

Các đường dẫn mặc định ở dưới. Lấy configuration-id từ tệp khởi tạo và credential-key từ chính sách; dùng đường dẫn cài đặt thực tế. Tệp khởi tạo chứa AK/SK: hạn chế quyền đọc, xóa bản tải xuống sau cài đặt và bảo vệ cấu hình đã cài.

- JSON: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env`
- Unix Socket: `/run/jumpserver-pam/<configuration-id>/agent.sock`

JSON giao tệp, EnvironmentFile dùng dịch vụ systemd cố định, Unix Socket cung cấp API cục bộ. Agent ghi phiên bản đã giao sau thành công; ứng dụng ghi phiên bản đã áp dụng sau kiểm tra và sử dụng. Socket thuộc người dùng ứng dụng với quyền 0600; gửi yêu cầu bằng người dùng đó.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env
```

Unit systemd phải tham chiếu EnvironmentFile. Chỉ dùng reload khi ứng dụng đọc lại tệp; reload không đưa biến môi trường mới vào tiến trình đang chạy. Đường dẫn, người dùng, dịch vụ và thao tác được cố định khi cài; mở rộng quyền cần cài lại.

### API cục bộ và xác nhận

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

Với luân phiên hai tài khoản, xác minh kết nối thật, chuyển nhóm kết nối và giải phóng kết nối cũ trước khi xác nhận đúng key, revision và account_id. Đăng ký thay đổi thông tin xác thực không cần xác nhận. Không xác nhận khi kiểm tra kết nối thất bại.

```bash
/opt/jumpserver-pam/venv/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jumpserver-pam/<configuration-id>/agent.sock'
```

Chỉ luân phiên cần confirm. Xác nhận cục bộ được lưu bền vững trước; confirmed nghĩa là Core đã nhận, pending nghĩa là sẽ thử lại. Không xác nhận chỉ vì ghi tệp hoặc khởi động lại dịch vụ thành công.

### Khắc phục sự cố

```bash
sudo systemctl status 'jms-pam-agent-<configuration-id>.service' --no-pager
sudo journalctl -u 'jms-pam-agent-<configuration-id>.service' -n 100 --no-pager
sudo systemctl restart 'jms-pam-agent-<configuration-id>.service'
```

Agent đồng bộ lúc khởi động, theo sự kiện liên quan và mỗi 300 giây. Lỗi mạng giữ bộ nhớ đệm đã được cấp quyền. Khi danh tính/quyền bị từ chối, chặn lấy qua Socket; đồng bộ có chữ ký thành công sẽ khôi phục. Tệp đã giao vẫn được giữ. SIGINT/SIGTERM đóng dịch vụ, kết nối và luồng đọc.

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
from jms_pam_config import client_options


with Client(instance_id="app-node-1", **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### Sự kiện và áp dụng thông tin xác thực

Xử lý snapshot ban đầu/khi kết nối lại và credential.updated. Ví dụ tách subscription với alternating_rotation. Triển khai apply_credential để xác minh kết nối thật, chuyển nhóm kết nối và giải phóng kết nối cũ. Hàm giữ chỗ phát sinh lỗi để ngăn xác nhận thông tin chưa áp dụng.

```python
from jms_pam import Client
from jms_pam_config import client_options


def apply_credential(credential):
    raise NotImplementedError('Hãy triển khai và xác minh việc chuyển thông tin xác thực của ứng dụng')


with Client(instance_id="app-node-1", **client_options) as client:
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
            if mode == "subscription" and account_id:
                credential = client.get_credential(account_id=account_id)
            elif mode == "alternating_rotation" and key:
                credential = client.get_credential(key=key)
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

### Lệnh ứng dụng

Dùng list_application_commands để lấy yêu cầu chờ và execute_application_command(event, handler) để nhận quyền thực thi. Chỉ chạy khi accepted là true. Hàm chuyển kiểm tra tài khoản/phiên bản yêu cầu, áp dụng và xác nhận; hàm khởi động lại phải kiểm tra sức khỏe trước khi báo thành công. Lỗi báo cáo thất bại không che lỗi xử lý ban đầu.

### Phương thức thông dụng

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

with hoặc close đóng phiên HTTP và luồng sự kiện; clone tạo phiên độc lập. Lỗi HTTP, mạng, xác thực và phân tích tạo PAMError có code, status_code, detail, original_error. Thử lại lỗi tạm thời tại ranh giới ứng dụng, xử lý rõ việc từ chối quyền và không ghi thông tin xác thực.

Mã mới dùng phương thức từ khóa snake_case và thuộc tính dataclass. API đối tượng yêu cầu credential.v1 cũ vẫn có với DeprecationWarning. SDK và Agent dùng giao thức phiên bản 1; sync_agent nhận KnownRevision cho phiên bản lưu đệm và đã giao.

<!-- sdk-doc:end -->

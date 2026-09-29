# cURL — Hướng dẫn sử dụng

Thư mục này chứa tập lệnh HTTP có chữ ký để chẩn đoán API account-secret cũ. Để tích hợp ứng dụng, dùng SDK Python, Go, Java hoặc Node.js.

## Yêu cầu môi trường

- Bash / cURL / OpenSSL / base64
- `demo.sh`

Cần Bash, cURL, OpenSSL và base64. Thay ASSET và ACCOUNT; bảo đảm chuỗi truy vấn dùng để ký được mã hóa đúng như cURL thực sự gửi.

## Cấu hình và chạy

Tạo ứng dụng trong Quản lý ứng dụng và cấp quyền cho tài khoản tài sản đích. Điền điểm cuối, AK/SK của ứng dụng và ID tổ chức bên dưới; thay mọi giá trị giữ chỗ trước khi chạy.

```bash
cd apps/accounts/clients/curl
export API_URL='https://jumpserver.example.com'
export API_KEY_ID='<app-id>'
export API_KEY_SECRET='<app-secret>'
export ORG_ID='<org-id>'

bash demo.sh
```

Ví dụ mặc định truy vấn tài sản ubuntu_docker và tài khoản root. Đổi thành tên thực tế đã được cấp quyền trong mã. Chạy lệnh từ thư mục gốc kho mã. Kết quả chứa bí mật, không đưa vào nhật ký ứng dụng.

## Yêu cầu và phản hồi

```http
GET /api/v1/accounts/integration-applications/account-secret/?asset=ubuntu_docker&account=root
```

```json
{"id":"<app-id>","secret":"<account-secret>"}
```

id xác định ứng dụng, không phải phiên bản tài khoản. secret là null có thể do cấu hình xem bí mật của máy chủ. Các ví dụ này chưa nhận sự kiện thông tin xác thực, báo cáo phiên bản đã áp dụng hoặc thực thi lệnh ứng dụng.

## Khắc phục sự cố

Với 401, kiểm tra AK/SK, tổ chức, giờ máy chủ và URL đã ký. Với 403, kiểm tra trạng thái ứng dụng và quyền tài khoản. Với 400, kiểm tra bộ chọn tài sản/tài khoản và mã hóa URL. Không ghi bí mật hoặc tiêu đề Authorization; tên phải khớp tài nguyên được cấp quyền.

## Tích hợp chính sách thông tin xác thực

Chi tiết chữ ký và bảng giao thức dưới đây dùng để chẩn đoán. Dùng phương thức SDK cho chính sách thông tin xác thực hoặc Python Agent qua tệp JSON, EnvironmentFile hay Unix Socket.

| HTTP | API | JSON / query |
| --- | --- | --- |
| GET | `/api/v1/accounts/credential-client/credential/` | `instance_id`, `key` / `account_id` |
| POST | `/api/v1/accounts/credential-client/confirm/` | `instance_id`, `key`, `revision`, `account_id` |
| GET | `/api/v1/accounts/credential-client/commands/` | `instance_id` |
| POST | `/api/v1/accounts/credential-client/command-result/` | `instance_id`, `command_id`, `status`, `error_code` |
| WebSocket | `/ws/accounts/credential-events/` | `instance_id` |

Ký HMAC-SHA256 theo thứ tự tiêu đề bên dưới. request-target chứa đường dẫn và truy vấn đã mã hóa, Digest dùng SHA-256 của đúng phần thân, X-JMS-Request-ID là UUID duy nhất, Date là thời gian HTTP UTC. Đặt X-JMS-Client-Version, X-JMS-Protocol-Version: 1 và X-JMS-Config-Schema-Version: 0 cho SDK. API và WebSocket dùng AK/SK ứng dụng cùng instance_id ổn định, duy nhất; tạo lại chữ ký cho mỗi yêu cầu và lần kết nối lại.

```text
(request-target) accept date digest x-jms-request-id x-jms-org
x-jms-client-version x-jms-protocol-version x-jms-config-schema-version
```

Với luân phiên hai tài khoản, xác minh kết nối thật, chuyển nhóm kết nối và giải phóng kết nối cũ trước khi xác nhận đúng key, revision và account_id. Đăng ký thay đổi thông tin xác thực không cần xác nhận. Không xác nhận khi kiểm tra kết nối thất bại.

received chỉ có nghĩa là đã đọc sự kiện. Trước khi xử lý sự kiện nghiệp vụ có event_id, gửi received trên cùng WebSocket; snapshot và pong không cần biên nhận. Đồng bộ ảnh chụp mỗi lần kết nối/kết nối lại, xử lý credential.updated, thu hồi quyền và thay đổi cấu hình.

# JumpServer PAM Go SDK

SDK này theo chức năng của SDK chính sách thông tin xác thực Python: lấy theo tài khoản được phép hoặc chính sách luân phiên, xác nhận phiên bản áp dụng, theo dõi sự kiện, xử lý lệnh và đồng bộ Agent. URL, chữ ký HMAC, Digest, thời gian UTC, ID yêu cầu và tiêu đề được tạo tự động.

## Yêu cầu môi trường

- Go 1.23+ / coder/websocket
- `cmd/demo/main.go`

## Cấu hình và chạy

Cài SDK nguồn và cấu hình bên dưới. Cấp quyền tài khoản cho pull trong quản lý ứng dụng; chỉ gắn chính sách khi cần push hoặc luân phiên thông tin xác thực. Lấy AK/SK và ID tổ chức từ tài liệu kết nối. Thay các giá trị mẫu và bảo vệ bí mật triển khai. Mỗi bản sao cần ID ổn định và duy nhất. Chỉ dùng một bộ chọn: ID tài khoản hoặc key chính sách.

```bash
cd apps/accounts/clients/go
export JMS_ENDPOINT='https://jumpserver.example.com'
export JMS_APP_ID='<app-id>'
export JMS_APP_SECRET='<app-secret>'
export JMS_ORG_ID='<org-id>'
export JMS_INSTANCE_ID='app-node-1'
export JMS_ACCOUNT_ID='<account-id>'

go mod download
go run ./cmd/demo
```

Các SDK hiện được cài từ mã nguồn kho này và chưa được phát hành lên kho gói công khai. Thay /path/to/jumpserver bằng đường dẫn tuyệt đối. Chạy lệnh cài Go và Node.js trong thư mục ứng dụng hoặc thêm phụ thuộc Java vào pom.xml của ứng dụng. Thay lệnh nhập cục bộ trong ví dụ bằng lệnh nhập gói dưới đây.

```bash
go mod edit -replace=github.com/jumpserver/jumpserver/apps/accounts/clients/go=/path/to/jumpserver/apps/accounts/clients/go
go get github.com/jumpserver/jumpserver/apps/accounts/clients/go@v0.0.0
```

```go
import pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
```

## Yêu cầu và phản hồi

```go
package main

import (
	"context"
	"fmt"
	"log"
	"os"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

func main() {
	client, err := pam.NewClient(pam.Options{
		Endpoint:   os.Getenv("JMS_ENDPOINT"),
		AppID:      os.Getenv("JMS_APP_ID"),
		AppSecret:  os.Getenv("JMS_APP_SECRET"),
		InstanceID: os.Getenv("JMS_INSTANCE_ID"),
		OrgID:      os.Getenv("JMS_ORG_ID"),
	})
	if err != nil {
		log.Fatal("Invalid SDK configuration")
	}
	defer client.Close()
	credential, err := client.GetCredential(context.Background(), pam.CredentialSelector{AccountID: os.Getenv("JMS_ACCOUNT_ID")})
	if err != nil {
		log.Fatalf("Credential fetch failed: %T", err)
	}
	// Pass credential.Account.Username / Secret to the application connection pool.
	fmt.Printf("Fetched revision %d; implement application credential switching.\n", credential.Revision)
}
```

## Hàm xử lý sự kiện

Khởi tạo trạng thái cục bộ trước khi lắng nghe. Python và Node.js dùng lớp con, Go dùng EventHandlers, Java dùng CredentialEventListener. Hãy triển khai việc chuyển kết nối thật trong ví dụ. API cũ vẫn được giữ lại.

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

type application struct {
	client      *pam.Client
	credentials map[string]pam.Credential
	modes       map[string]string
}

func (a *application) observe(ctx context.Context, event pam.Event) error {
	updates := []pam.Event{event}
	if event.Event == "snapshot" {
		clear(a.modes)
		updates = event.Credentials
	}
	for _, update := range updates {
		key := update.CredentialKey
		if key == "" {
			key = update.Key
		}
		if key != "" && (event.Event == "snapshot" || event.Event == "credential.updated") {
			a.modes[key] = update.CredentialMode
		}
	}
	if event.Event == "snapshot" {
		for key := range a.credentials {
			if _, ok := a.modes[key]; !ok {
				delete(a.credentials, key) /* Also release connections. */
			}
		}
	}
	// Use ExecuteApplicationCommand for command events; see cmd/events/main.go.
	return nil
}
func applyCredential(ctx context.Context, credential pam.Credential) error {
	return fmt.Errorf("implement connection validation, pool switching and old connection cleanup")
}
func (a *application) changed(ctx context.Context, credential pam.Credential) error {
	if err := applyCredential(ctx, credential); err != nil {
		return err
	}
	if a.modes[credential.Key] == "alternating_rotation" {
		if _, err := a.client.ConfirmCredential(ctx, credential.Key, credential.Revision, credential.Account.ID); err != nil {
			return err
		}
	}
	a.credentials[credential.Key] = credential
	return nil
}
func (a *application) revoked(ctx context.Context, event pam.Event) error {
	delete(a.credentials, event.CredentialKey) // Also release affected connections.
	return nil
}
func main() {
	client, err := pam.NewClient(pam.Options{Endpoint: os.Getenv("JMS_ENDPOINT"), AppID: os.Getenv("JMS_APP_ID"), AppSecret: os.Getenv("JMS_APP_SECRET"), InstanceID: os.Getenv("JMS_INSTANCE_ID"), OrgID: os.Getenv("JMS_ORG_ID")})
	if err != nil {
		log.Fatal("Invalid SDK configuration")
	}
	defer client.Close()
	app := &application{client: client, credentials: make(map[string]pam.Credential), modes: make(map[string]string)}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	err = client.WatchEvents(ctx, pam.EventHandlers{OnEvent: app.observe, OnCredentialChanged: app.changed, OnCredentialRevoked: app.revoked})
	if err != nil && !errors.Is(err, context.Canceled) {
		log.Printf("Event processing failed: %T", err)
	}
}
```

snapshot ban đầu, khi kết nối lại và credential.updated lấy thông tin theo chế độ rồi gọi hàm xử lý tuần tự. Bộ đọc dùng hàng đợi giới hạn 128 sự kiện; khi đầy sẽ tạo áp lực ngược. Lỗi lấy hoặc áp dụng được thử lại với thời gian chờ tăng theo hàm mũ 1–30 giây, mỗi lần đều lấy lại. Sự kiện mới thay thế lần thử của cùng mục tiêu; snapshot đặt lại phạm vi, thu hồi và thay đổi cấu hình hủy các lần thử. Hàm xử lý phải gọi lặp lại an toàn. Hàm quan sát và thu hồi không tự thử lại; lệnh phải được nhận quyền thực thi. received chỉ nghĩa là đã đọc; SDK không tự xác nhận luân chuyển. Sự kiện phiên bản cũ không hủy lần lấy lại đang chờ cho phiên bản mới hơn.

`WatchEvents(ctx, handlers)` / `StartEvents(ctx, handlers)`; `Stop()` / `Wait()`; `context.CancelFunc`

WatchEvents chờ trong goroutine gọi; StartEvents không đảm bảo đồng bộ ban đầu. Một bộ lắng nghe mỗi client. Stop và Close yêu cầu hủy; gọi Wait bên ngoài hàm xử lý. Tác vụ dài phải xử lý việc hủy context.

### Thông tin xác thực mới nhất và lỗi máy chủ

Luôn gọi API trước. Kết quả thành công thay thế giá trị đang giữ; phiên bản cũ không ghi đè bản mới và không có thời hạn hết hiệu lực theo thời gian. Chỉ hết thời gian chờ, lỗi mạng hoặc HTTP 5xx mới trả về giá trị thành công gần nhất của cùng bộ chọn với cờ nguồn cục bộ. Chưa có giá trị thì báo lỗi gốc. SDK giữ trong bộ nhớ client đến khi cập nhật, thu hồi hoặc đóng; clone và khởi động lại bắt đầu trống. Agent dùng trạng thái cục bộ được bảo vệ sẵn có. HTTP 401/403/404 hoặc client_upgrade_required xóa giá trị SDK rồi báo lỗi; phản hồi thành công không hợp lệ cũng báo lỗi. Thu hồi xóa mục liên quan, snapshot xóa mục ngoài quyền. Thay đổi cấu hình giữ giá trị đến khi kiểm tra snapshot tiếp theo. Agent áp dụng thu hồi rõ ràng và thu hẹp phạm vi snapshot trước khi đồng bộ HTTP, lưu phạm vi đó và chặn các lần lấy cục bộ liên quan ngay cả khi máy chủ lỗi hoặc sau khi khởi động lại. Phản hồi credential_not_found (HTTP 400) cũng xóa giá trị SDK được giữ lại. Pull trực tiếp bằng account_id luôn cần phản hồi API trực tiếp; snapshot push không xác nhận quyền dùng giá trị pull đã lưu.

- `credential.FromLocal`
- `GetCredentialFresh(ctx, selector)`

Khi bật lắng nghe được quản lý, snapshot và credential.updated tự lấy dữ liệu, thay thế giá trị và gọi hàm nghiệp vụ. Lỗi cập nhật giữ bản trước và thử lại. Agent cũng lấy lại theo thông báo, giữ dữ liệu khi máy chủ lỗi. Dùng lời gọi bắt buộc API bên dưới để cập nhật hay chuyển kết nối; giá trị đang giữ không phải phiên bản vừa lấy và không tự xác nhận luân chuyển.

Khi nhàn rỗi gửi ping mỗi 10 giây; khoảng 30 giây không có tin nhắn sẽ kết nối lại, chờ tăng theo hàm mũ 1–30 giây và ký mới. snapshot khôi phục trạng thái hiện tại, không phát lại lịch sử.



## Sự kiện và áp dụng thông tin xác thực

Xử lý snapshot đầu tiên/kết nối lại và credential.updated. Ví dụ đầy đủ xử lý subscription, alternating_rotation và lệnh. Triển khai kiểm tra kết nối thực, chuyển nhóm kết nối và giải phóng kết nối cũ. Hàm mẫu ném lỗi để ngăn xác nhận trước khi áp dụng. Xóa khỏi trạng thái ứng dụng các tài khoản không còn trong snapshot và xử lý thu hồi.

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

func applyCredential(credential pam.Credential) error {
	return fmt.Errorf("implement connection validation, pool switching and old connection cleanup")
}
func restartApplication() error { return fmt.Errorf("implement application restart and health check") }
func handleCommand(ctx context.Context, client *pam.Client, event pam.Event) error {
	if event.Event == "application.restart.requested" {
		return restartApplication()
	}
	if event.Event != "credential.switch.requested" {
		return fmt.Errorf("unsupported application command")
	}
	credential, err := client.GetCredentialFresh(ctx, pam.CredentialSelector{Key: event.CredentialKey})
	if err != nil {
		return err
	}
	if credential.Revision != event.Revision || credential.Account.ID != event.AccountID {
		return fmt.Errorf("requested account version is superseded")
	}
	if err = applyCredential(credential); err != nil {
		return err
	}
	_, err = client.ConfirmCredential(ctx, credential.Key, credential.Revision, credential.Account.ID)
	return err
}
func main() {
	client, err := pam.NewClient(pam.Options{Endpoint: os.Getenv("JMS_ENDPOINT"), AppID: os.Getenv("JMS_APP_ID"), AppSecret: os.Getenv("JMS_APP_SECRET"), InstanceID: os.Getenv("JMS_INSTANCE_ID"), OrgID: os.Getenv("JMS_ORG_ID")})
	if err != nil {
		log.Fatal("Invalid SDK configuration")
	}
	defer client.Close()
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	err = client.WatchCredentialEvents(ctx, func(event pam.Event) error {
		if event.CommandID != "" {
			client.ExecuteApplicationCommand(ctx, event, func(command pam.Event) error { return handleCommand(ctx, client, command) })
			return nil
		}
		updates := []pam.Event{}
		if event.Event == "snapshot" {
			updates = event.Credentials
		} else if event.Event == "credential.updated" {
			updates = []pam.Event{event}
		}
		// On snapshots, remove application caches absent from the new authorized scope.
		for _, update := range updates {
			key := update.CredentialKey
			if key == "" {
				key = update.Key
			}
			selector := pam.CredentialSelector{}
			if update.CredentialMode == "subscription" && update.AccountID != "" && key != "" {
				if !strings.HasSuffix(key, ":"+update.AccountID) {
					key += ":" + update.AccountID
				}
				selector.Key = key
			} else if update.CredentialMode == "alternating_rotation" && key != "" {
				selector.Key = key
			} else {
				continue
			}
			credential, err := client.GetCredentialFresh(ctx, selector)
			if err != nil {
				return err
			}
			if err = applyCredential(credential); err != nil {
				return err
			}
			if update.CredentialMode == "alternating_rotation" {
				if _, err = client.ConfirmCredential(ctx, credential.Key, credential.Revision, credential.Account.ID); err != nil {
					return err
				}
			}
		}
		return nil
	})
	if err != nil && !errors.Is(err, context.Canceled) {
		log.Fatalf("Credential processing failed: %T", err)
	}
}
```

Với luân phiên hai tài khoản, xác minh kết nối thật, chuyển nhóm kết nối và giải phóng kết nối cũ trước khi xác nhận đúng key, revision và account_id. Đăng ký thay đổi thông tin xác thực không cần xác nhận. Không xác nhận khi kiểm tra kết nối thất bại.

## Lệnh ứng dụng

Thăm dò, nhận quyền thực thi và báo cáo kết quả dùng phương thức SDK. Chỉ nhận quyền thành công mới chạy hàm xử lý. Chuyển đổi kiểm tra phiên bản và tài khoản, áp dụng rồi xác nhận; khởi động lại phải kiểm tra tình trạng sau khởi động. Chỉ báo thành công khi hoàn tất. Lỗi báo cáo không thay thế lỗi nghiệp vụ gốc.

## Phương thức thông dụng

- `GetCredential(ctx, CredentialSelector{Key: ...})`
- `GetCredential(ctx, CredentialSelector{AccountID: ...})`
- `GetCredentialFresh(ctx, selector)`
- `ConfirmCredential(ctx, key, revision, accountID)`
- `WatchEvents(ctx, EventHandlers{...}) / StartEvents(ctx, handlers)`
- `EventWatcher.Stop() / EventWatcher.Wait()`
- `WatchCredentialEvents(ctx, handler)`
- `ListApplicationCommands(ctx)`
- `ReportApplicationCommandResult(ctx, commandID, status, errorCode)`
- `ExecuteApplicationCommand(ctx, event, handler)`
- `SyncAgent(ctx, AgentSyncOptions{...})`
- `Clone() / Close()`

## Khắc phục sự cố

Lỗi HTTP, mạng, xác thực và giải mã dùng kiểu lỗi SDK với mã và trạng thái HTTP. Đóng luồng và máy khách sau khi dùng; bản sao có vòng đời độc lập. Thử lại lỗi tạm thời ở tầng ứng dụng và không ghi bí mật hay tiêu đề xác thực vào nhật ký.

`PAMError`

Mọi SDK dùng giao thức phiên bản 1; Agent dùng lược đồ cấu hình phiên bản 1. Khi nhận client_upgrade_required (HTTP 426), kiểm tra tương thích và nâng cấp. Cho phép trường tùy chọn và thông báo chưa biết; không áp dụng hay xác nhận chính sách chưa hỗ trợ. Biên nhận được gửi tự động và không chứng minh đã áp dụng thông tin xác thực.

## Tích hợp Go Agent

Danh tính dùng app_id, app_secret, org_id và instance_id ổn định; quyền theo chính sách gắn với ứng dụng. Đường dẫn và thao tác dịch vụ đều ở máy cục bộ: state_file giữ mật khẩu mới nhất, event_file ghi sự kiện không có bí mật, delivery chọn đầu ra mặc định, rules đặt tệp, mẫu và reload/restart hoặc tập lệnh cố định. Khi nhận thông báo, Agent lấy và lưu mật khẩu hiện tại, thay tệp nguyên tử rồi chạy thao tác; lỗi sẽ được thử lại. Dùng credentials[].key từ get_accounts cho rules; key đăng ký chứa ID tài khoản. rules rỗng ghi một tệp cho mỗi key.

rules cục bộ cấu hình tệp, JSON/EnvironmentFile hoặc mẫu tin cậy cùng systemd reload/restart hoặc chương trình cố định. Script nhận JSON qua stdin, dùng đối số cố định và giới hạn thời gian, rồi kiểm tra ứng dụng trước khi báo thành công. Core không được mở rộng quyền này. Khởi động lại Agent sau khi sửa cấu hình riêng tư.

Cấu hình tải về đã có danh tính và thiết lập phân phối của Agent. Trong rules, khai báo ID tài khoản ứng dụng sử dụng, cách cập nhật cấu hình, áp dụng thay đổi và kiểm tra kết nối đang chạy. allow_account_switch dùng cùng một quy tắc cho cả hai chiều luân phiên A/B. credential_check tùy chọn kiểm tra đăng nhập mới trước khi sửa tệp. Đường dẫn trạng thái, sự kiện, Socket và chu kỳ đối chiếu 300 giây có giá trị mặc định. rules rỗng ghi tệp mặc định cho từng thông tin xác thực.

```json
{
  "endpoint": "https://jumpserver.example.com",
  "app_id": "<application-id>",
  "app_secret": "<application-secret>",
  "org_id": "<org-id>",
  "instance_id": "orders-node-1",
  "delivery": {
    "delivery_mode": "json",
    "delivery_root": "/opt/jumpserver-pam/credentials",
    "app_user": "orders"
  },
  "rules": []
}
```

`rules`:

```json
[
  {
    "accounts": [
      {
        "account_id": "<primary-account-id>",
        "allow_account_switch": true
      }
    ],
    "config_update": {
      "file": "/etc/order-service/config.yml",
      "fields_map": {
        "DB_USER": "username",
        "DB_PASSWORD": "secret"
      }
    },
    "service_action": {
      "unit": "order-service.service",
      "operation": "restart"
    },
    "application_check": {
      "path": "/usr/local/libexec/jms-pam/check-running-db",
      "confirm_on_success": true
    }
  }
]
```

```bash
jms-pam-agent get_accounts
jms-pam-agent get_secret '<account-id>'
sudo jms-pam-agent check-config
sudo systemctl restart jms-pam-agent
```

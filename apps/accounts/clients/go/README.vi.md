# JumpServer PAM Go SDK

SDK này theo chức năng của SDK chính sách thông tin xác thực Python: lấy theo tài khoản được phép hoặc chính sách luân phiên, xác nhận phiên bản áp dụng, theo dõi sự kiện, xử lý lệnh và đồng bộ Agent. URL, chữ ký HMAC, Digest, thời gian UTC, ID yêu cầu và tiêu đề được tạo tự động.

## Yêu cầu môi trường

- Go 1.23+ / coder/websocket
- `cmd/demo/main.go`

## Cấu hình và chạy

Cài SDK nguồn và cấu hình bên dưới. Cấp quyền tài khoản và gắn chính sách trong quản lý ứng dụng; lấy AK/SK và ID tổ chức từ tài liệu kết nối. Thay các giá trị mẫu và bảo vệ bí mật triển khai. Mỗi bản sao cần ID ổn định và duy nhất. Chỉ dùng một bộ chọn: ID tài khoản hoặc key chính sách.

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

## Sự kiện và áp dụng thông tin xác thực

Xử lý snapshot đầu tiên/kết nối lại và credential.updated. Ví dụ đầy đủ xử lý subscription, alternating_rotation và lệnh. Triển khai kiểm tra kết nối thực, chuyển nhóm kết nối và giải phóng kết nối cũ. Hàm mẫu ném lỗi để ngăn xác nhận trước khi áp dụng. Xóa khỏi bộ nhớ đệm các tài khoản không còn trong snapshot và xử lý thu hồi.

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
	credential, err := client.GetCredential(ctx, pam.CredentialSelector{Key: event.CredentialKey})
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
			if update.CredentialMode == "subscription" && update.AccountID != "" {
				selector.AccountID = update.AccountID
			} else if update.CredentialMode == "alternating_rotation" && key != "" {
				selector.Key = key
			} else {
				continue
			}
			credential, err := client.GetCredential(ctx, selector)
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
- `ConfirmCredential(ctx, key, revision, accountID)`
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

## Tích hợp Linux Agent

Đồng bộ phục vụ triển khai Agent. Cần danh tính hoặc source Agent và ID cấu hình, dùng KnownRevision cho phiên bản đệm và đã chuyển giao. Cài đặt Linux, chuyển giao tệp và API cục bộ hiện do Python Agent cung cấp, ứng dụng mọi ngôn ngữ đều có thể dùng.

# JumpServer PAM Go SDK

本 SDK 与 Python 凭据策略 SDK 对齐：获取授权账号或轮换策略凭据、确认生效版本、监听事件、处理应用指令、同步 Agent 状态。请求 URL、HMAC 签名、Digest、UTC 时间、请求 ID 和协议头均由客户端自动生成。

## 环境要求

- Go 1.23+ / coder/websocket
- `cmd/demo/main.go`

## 配置与运行

安装源码 SDK，填写下方配置。在应用管理中授权账号并绑定策略，从应用接入材料获取应用 AK/SK 和组织 ID。替换占位符，将身份材料保存在部署密钥中，每个副本使用稳定、唯一的实例 ID。取密只能选择账号 ID 或策略 key 中的一种。

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

SDK 当前从本仓库源码安装，尚未发布到公共包仓库。将 /path/to/jumpserver 替换为绝对路径；Go 和 Node.js 安装命令在应用目录执行，Java 依赖添加到应用 pom.xml。仓库运行示例的本地导入在应用中应替换为下方包导入。

```bash
go mod edit -replace=github.com/jumpserver/jumpserver/apps/accounts/clients/go=/path/to/jumpserver/apps/accounts/clients/go
go get github.com/jumpserver/jumpserver/apps/accounts/clients/go@v0.0.0
```

```go
import pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
```

## 请求与响应

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

## 事件与凭据生效

处理首次/重连 snapshot 和 credential.updated。下方完整事件示例分别处理 subscription、alternating_rotation 及应用指令。替换凭据应用函数：验证真实连接、切换连接池并释放旧连接。占位函数会抛出异常，防止确认尚未应用的版本；应用缓存还须按快照移除已撤销账号，并处理撤销事件。

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

交替轮换需要先验证真实连接、切换应用连接池并释放旧连接，再确认准确的 key、revision 和 account_id。凭据变更订阅无需确认，连接验证失败时不得确认。

## 应用指令

轮询、指令认领和结果上报均通过 SDK 方法完成，只有认领成功才执行处理函数。切换指令校验请求的版本与账号、应用凭据后再确认；重启指令须完成重启及健康检查。工作完成后才报告成功，失败上报不会掩盖原始业务异常。

## 常用方法

- `GetCredential(ctx, CredentialSelector{Key: ...})`
- `GetCredential(ctx, CredentialSelector{AccountID: ...})`
- `ConfirmCredential(ctx, key, revision, accountID)`
- `WatchCredentialEvents(ctx, handler)`
- `ListApplicationCommands(ctx)`
- `ReportApplicationCommandResult(ctx, commandID, status, errorCode)`
- `ExecuteApplicationCommand(ctx, event, handler)`
- `SyncAgent(ctx, AgentSyncOptions{...})`
- `Clone() / Close()`

## 排查问题

HTTP、网络、认证和响应解码错误使用 SDK 异常或错误类型，包含错误码及 HTTP 状态。使用完成后关闭事件流与客户端，克隆客户端具有独立生命周期。在业务边界重试临时故障，不记录密码或认证请求头。

`PAMError`

各 SDK 使用版本 1 协议，Agent 配置格式为版本 1。收到 client_upgrade_required（HTTP 426）时检查兼容性并升级。允许未知可选字段及通知事件，未实现的策略类型不得应用或确认。事件接收回执由 SDK 自动发送，不能作为凭据已经生效的证明。

## Linux Agent 接入

Agent 同步方法供 Agent 实现复用，需要 Agent 身份或 source 及配置 ID，使用 KnownRevision 上报缓存与交付版本。目前 Linux 安装、文件交付和本地 API 由 Python Agent 提供，各编程语言的应用均可接入该 Agent。

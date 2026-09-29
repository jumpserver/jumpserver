# JumpServer PAM 客户端

本目录统一维护应用接入 JumpServer 的 SDK、Agent 和示例，按实现语言组织。

| 目录 | 当前能力 | 接入文档 |
| --- | --- | --- |
| `python/` | 完整 SDK、Linux Agent；Python 3.9+ | [中文](python/README.zh-hans.md) / [English](python/README.en.md) |
| `go/` | 完整 SDK；Go 1.23+ | [中文](go/README.zh-hans.md) / [English](go/README.en.md) |
| `java/` | 完整 SDK；Java 11+ | [中文](java/README.zh-hans.md) / [English](java/README.en.md) |
| `node/` | 完整 SDK、TypeScript 类型声明；Node.js 20.3+ | [中文](node/README.zh-hans.md) / [English](node/README.en.md) |
| `curl/` | 旧账号取密接口的协议调试脚本 | [中文](curl/README.zh-hans.md) / [English](curl/README.en.md) |

四种语言的 SDK 以 Python 为功能基准，封装同一套凭据客户端协议。应用只传入服务端地址、应用 AK/SK、组织及实例配置，调用客户端方法即可；API 路径、查询编码、HMAC 签名、Digest、UTC 时间、请求 ID 和版本头由 SDK 自动生成。HTTP 请求和 WebSocket 重连都会重新签名。

## SDK 功能对应

| 功能 | Python | Go | Java | Node.js |
| --- | --- | --- | --- | --- |
| 按账号取密 | `get_credential(account_id=...)` | `GetCredential(ctx, CredentialSelector{AccountID: ...})` | `getCredentialByAccountId(accountId)` | `getCredential({accountId})` |
| 按策略取密 | `get_credential(key=...)` | `GetCredential(ctx, CredentialSelector{Key: ...})` | `getCredential(key)` | `getCredential({key})` |
| 确认生效版本 | `confirm_credential(...)` | `ConfirmCredential(...)` | `confirmCredential(...)` | `confirmCredential({...})` |
| 监听事件及重连快照 | `watch_credential_events(...)` | `WatchCredentialEvents(ctx, handler)` | `watchCredentialEvents()` | `watchCredentialEvents({...})` |
| 查询待处理指令 | `list_application_commands()` | `ListApplicationCommands(ctx)` | `listApplicationCommands()` | `listApplicationCommands()` |
| 认领并执行指令 | `execute_application_command(event, handler)` | `ExecuteApplicationCommand(ctx, event, handler)` | `executeApplicationCommand(event, handler)` | `executeApplicationCommand(event, handler)` |
| 上报指令结果 | `report_application_command_result(...)` | `ReportApplicationCommandResult(...)` | `reportApplicationCommandResult(...)` | `reportApplicationCommandResult({...})` |
| Agent 状态同步 | `sync_agent(...)` | `SyncAgent(ctx, options)` | `syncAgent(...)` | `syncAgent({...})` |
| 生命周期 | `clone()` / `close()` / `with` | `Clone()` / `Close()` | `clone()` / `close()` / try-with-resources | `clone()` / `close()` |

每个客户端实例对应一个稳定、唯一的应用副本 ID。取密返回结构化凭据与版本，错误包含错误码及 HTTP 状态。事件接收回执自动发送，仅表示读取事件。交替轮换必须在验证真实连接、切换连接池并释放旧连接后确认准确的版本；凭据订阅无需确认。指令只有认领成功才执行，业务处理失败的原始错误会保留。

各 SDK 使用协议版本 1，Agent 配置版本为 1。遇到 `client_upgrade_required`（HTTP 426）需检查兼容性并升级；未知可选字段和通知事件可以传给应用，未实现的策略类型不得应用或确认。

## 在应用中安装 SDK

当前通过本仓库源码安装；以下路径替换为本地绝对路径。这些包尚未发布到公共包仓库。

### Python

```bash
python3 -m pip install /path/to/jumpserver/apps/accounts/clients/python
```

导入：`from jms_pam import Client`。

### Go

在应用的 Go module 目录执行：

```bash
go mod edit -replace=github.com/jumpserver/jumpserver/apps/accounts/clients/go=/path/to/jumpserver/apps/accounts/clients/go
go get github.com/jumpserver/jumpserver/apps/accounts/clients/go@v0.0.0
```

导入：`import pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"`。示例位于 `go/cmd/demo/` 和 `go/cmd/events/`。

### Java

先将 SDK 安装到本地 Maven 仓库：

```bash
mvn -f /path/to/jumpserver/apps/accounts/clients/java/pom.xml install
```

在应用的 `pom.xml` 添加：

```xml
<dependency>
  <groupId>org.jumpserver</groupId>
  <artifactId>jms-pam</artifactId>
  <version>1.0.0</version>
</dependency>
```

导入：`import org.jumpserver.pam.Client;`。示例为 `Demo.java` 和 `EventsDemo.java`。

### Node.js

```bash
npm install /path/to/jumpserver/apps/accounts/clients/node
```

导入：`const { Client } = require('@jumpserver/pam')`，ESM 可以使用 `import { Client } from '@jumpserver/pam'`。示例为 `node/demo.js` 和 `node/events.js`。

## 文档语言

每个客户端目录提供十种文档语言：英文、简体中文、繁体中文、日文、韩文、巴西葡萄牙文、俄文、越南文、西班牙文和法文，对应 `README.<locale>.md`。

文档中心可以选择编程语言，正文跟随界面语言；地区别名会映射到对应文档，未知或缺失的语言回退到英文。API 路径、配置字段和代码标识符保持原名。维护与生成方法见 [文档维护](docs/README.md)。

## Python SDK 与 Agent

- SDK 入口：`python/jms_pam/client.py`。
- 响应模型：`python/jms_pam/models.py`，使用带类型提示的 dataclass。
- Agent 命令入口：`python/jms_pam/agent.py`；运行、交付、本地 API 和安装源码位于 `python/jms_pam/_agent/`，复用同包内的 SDK。
- 分发包：`jms-pam`，安装后通过 `jms_pam` 导入 SDK，通过 `jms-pam-agent` 启动 Agent。
- 示例应用：`python/demo.py`、`python/postgresql_app.py`、`python/file_apps/`。

从仓库根目录安装：

```bash
python3 -m pip install -e ./apps/accounts/clients/python
```

详细接入说明：[中文](python/README.zh-hans.md)、[English](python/README.en.md)。

## 语言规范

凭据策略 SDK 与 Agent 使用统一的 HTTP / WebSocket 协议，新实现采用各自语言的接口习惯。

- Python 遵循 [PEP 8](https://peps.python.org/pep-0008/)：方法、参数和属性使用 `snake_case`，类使用 `CapWords`，通过关键字参数调用客户端，响应使用 dataclass，客户端支持上下文管理器。
- Go 遵循 [Effective Go](https://go.dev/doc/effective_go)，使用 `gofmt`、导出标识符和显式错误返回；耗时操作接受 `context.Context`。
- Java 使用 `UpperCamelCase` 类名和 `lowerCamelCase` 方法、字段。
- Node.js 使用 `camelCase` 方法、字段和 Promise / `async`、`await`。

Python 的原始 `credential.v1` 请求对象接口作为兼容入口保留；新接入统一使用 `from jms_pam import Client`。

## 后续 Go Agent

Go Agent 可在 `go/agent/` 下实现，按独立可执行文件构建和分发。该目录当前尚未提供 Go Agent。不同语言的 Agent 应复用 Core 的凭据客户端协议、事件流、应用生效确认和安装能力约束。

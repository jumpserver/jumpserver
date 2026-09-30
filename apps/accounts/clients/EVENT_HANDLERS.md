# SDK 事件处理接口

Python、Go、Java、Node.js 均已实现高层事件处理接口，保留原来的迭代器或回调入口。

## 接口与生命周期

| 语言 | 保留的入口 | 高层入口 | 停止和等待 |
| --- | --- | --- | --- |
| Python | `watch_credential_events(stop_event=...)` | 子类钩子；`watch_events()` / `start_events()` | `stop_events()` / `close()` 停止并等待；支持钩子内自行停止 |
| Go | `WatchCredentialEvents(ctx, handler)` | `EventHandlers`；`WatchEvents(ctx, handlers)` / `StartEvents(ctx, handlers)` | `Stop()` 或 context 取消；外部 `Wait()` 等待；`Client.Close()` 请求取消 |
| Java | `watchCredentialEvents()` 返回 `EventStream` | `CredentialEventListener`；`watchEvents(listener)` / `startEvents(listener)` | `EventSubscription.stop()` 请求停止；`close()` 停止并等待；外部 `awaitTermination()` 等待 |
| Node.js | `watchCredentialEvents({signal})` | 子类异步钩子；`watchEvents()` / `startEvents()` | `AbortSignal` 或 `stopEvents()`；外部等待 `subscription.stop()` / `done`；`close()` 同步请求取消 |

构造客户端时初始化本地状态，显式启动时建立事件连接。每个客户端允许一个高层监听器，停止后可重新启动。后台启动返回不代表首次同步完成，依赖凭据的服务应等待业务就绪。主线程与后台处理共享的业务状态由应用保护。

Python 的 `clone()` 重新构造同类型实例和本地状态；额外构造依赖由子类处理。Go、Java 返回独立客户端；Node.js 的 `clone()` 保持返回基础 `Client`。各语言 clone 均不继承保留值或监听器。

## 处理和恢复

- 首次及重连 `snapshot`、`credential.updated` 按策略模式取密：订阅按 `account_id`，交替轮换按 key。
- 原始事件钩子先执行，再执行凭据变更或撤销处理函数。生命周期事件不取密，指令仍通过 SDK 的认领接口执行业务处理。
- 独立读取器与串行处理函数使用容量 128 的有界队列，满载时产生背压。Node.js 钩子逐个 await；CPU 密集任务仍需要应用安排 worker。
- 取密或凭据处理失败按 1、2、4…30 秒退避重试，每次重新取密。同一目标的新事件替换重试，较旧版本事件不会取消较新版本的拉取重试；快照重置重试范围，撤销或配置变化取消待重试项。处理函数应支持重复调用。
- 原始事件和撤销处理函数的错误进入错误处理函数，不自动重试任意指令。默认日志仅输出错误类型，避免日志包含凭据。
- 事件连接空闲时每 10 秒发送应用层 ping，约 30 秒没有收到消息则重连。重连采用 1–30 秒指数退避并重新签名；快照恢复当前状态，不重放历史事件。
- `received` 仅表示读取事件。业务成功验证并切换连接后，由应用显式确认准确的 key、revision、account_id；订阅无需确认，SDK 不自动确认轮换。

## 保留已获取的最新凭据

启用高层事件监听后，首次与重连快照、后端凭据更新事件会自动获取当前凭据。获取成功后先更新 SDK 保留的最新值，再调用业务处理函数；业务处理失败不丢失这份凭据。刷新失败时保留上一份值，并继续退避重试。更旧的 API 版本不得覆盖已获取的新版本。

普通取密始终先请求 API。只有超时、网络故障或 HTTP 5xx 时，才返回同一查询条件下已获取的最新凭据，并标记本地来源。保留值没有 TTL，不随时间过期；首次取密失败且没有保留值时仍返回原始错误。

| 语言 | 本地来源标记 | 必须实时取密 |
| --- | --- | --- |
| Python | `from_local` | `get_credential(..., allow_local_fallback=False)` |
| Go | `FromLocal` | `GetCredentialFresh(ctx, selector)` |
| Java | `isFromLocal()` | `getCredential(key, false)` / `getCredentialByAccountId(id, false)` |
| Node.js | `fromLocal` | `getCredential({...selector, allowLocalFallback: false})` |

SDK 在当前客户端进程内存中保留最新值，关闭后释放；clone 和进程重启从空状态开始。Agent 使用已有受保护的本地状态保存凭据，收到更新通知后主动获取最新值，后端故障期间保留已有值。

Agent 收到明确撤销或授权范围缩小的快照时，先停用相应本地取密并持久化授权范围，再尝试 HTTP 同步；后端暂时不可用或 Agent 重启不会恢复已撤销的访问。整项订阅策略撤销同时停用其账号项。已经交付的业务文件仍按既有交付规则处理。

HTTP 401/403/404、`credential_not_found`（HTTP 400）或 `client_upgrade_required` 清空 SDK 保留值并报错；格式错误的成功响应不使用本地值。明确撤销删除对应项；授权快照删除范围外的项；配置变更通知先保留已有值，等待后续授权快照核对。已撤销的在途请求不能重新填充本地状态。

高层事件刷新与 Agent 始终实时取密；高层事件处理拒绝低于事件版本的 API 凭据。业务轮换切换示例也要求实时取密，保留值不被当作新版本且不自动确认轮换。原有低层事件入口继续返回事件，由现有业务代码调用取密接口；这些取密结果同样更新 SDK 保留值。

## 可运行示例与文档

- Python：[子类示例](python/subclass_demo.py)，应用接入向导提供完整混合策略及指令示例。
- Go：[回调组合示例](go/cmd/hooks/main.go)，处理函数接收 context。
- Java：[监听器示例](java/src/main/java/org/jumpserver/pam/HooksDemo.java)，用 try-with-resources 管理生命周期。
- Node.js：[异步子类示例](node/hooks.js)，取消信号传入异步钩子。

连接验证和切换函数是需要业务实现的占位函数，当前会抛错。现有调用形式的示例继续保留。四种 SDK 的十种语言文档同步说明了处理函数、重连、最新凭据与生命周期；生成入口为 `docs/build.py`。

本地测试覆盖签名协议、断线重连、首次与重连快照、慢处理、失败重试、取消、凭据保留、自动更新及权限边界。真实业务连接池切换需要在目标应用中验证。

## 独立 Go Agent

Agent 入口为 `go/cmd/jms-pam-agent`，运行逻辑位于 `go/agent`，以本机私有配置驱动默认文件、可信模板和有超时的 systemd 或固定脚本动作。服务固定为 `jms-pam-agent.service`，使用 `systemctl start jms-pam-agent`。脚本通过标准输入接收凭据，Core 不能扩大本机执行规则。取密或交付失败按 1–30 秒退避重试；交付不自动确认业务生效。Python 包不再注册 Agent 命令。

本地开发支持 `init-local` / `run --local`；签名授权范围仍来自 Core，本机路径和属主由当前用户配置。可选 `event_file` 追加收到、保存和交付阶段的事件元数据，不记录密码；最新密码单独保留在私有状态和交付文件中。CLI `get_accounts` 不取密码，`get_secret ACCOUNT_ID` 优先在线取密，只在 API 临时不可用时返回仍授权的保留值，JSON 标明 `source`。

# JumpServer PAM Python SDK 与 Go Agent

应用可以使用 Python SDK 直接连接 JumpServer，也可以在应用主机运行 Go Agent。Agent 可在 Linux、macOS 和 Windows 前台运行；内置 systemd 安装仅支持 Linux。客户端启动时获取轮换凭据，并通过签名认证的凭据事件流 WebSocket 接收订阅账号快照和后续更新；`credential.updated`、重连快照中的新版本以及管理员手动发送的账号切换请求会触发取密。

## 源码与本地安装

Python SDK 位于 `apps/accounts/clients/python`，分发包为 `jms-pam`；独立 Go Agent 位于 `apps/accounts/clients/go`：

- `jms_pam/client.py`：SDK 公共接口，负责凭据、同步和应用指令操作。
- `jms_pam/_transport.py`、`_events.py`、`_commands.py`：HTTP 会话、事件流和命令执行流程。
- `jms_pam/models.py`：使用 `snake_case` 字段的 dataclass 响应模型。
- `jms_pam/exceptions.py`：统一的 `PAMError` 异常。
- `../go/cmd/jms-pam-agent`：独立 Go Agent 入口，运行逻辑位于 `../go/agent`。
- `demo.py`、`postgresql_app.py`、`file_apps/`：使用 SDK 或 Agent 的示例应用。

从仓库根目录安装：

```bash
python3 -m pip install -e ./apps/accounts/clients/python
```

也可以从 JumpServer 下载 Python SDK 压缩包，在解压根目录运行 `python3 -m pip install .`，然后在同一目录运行示例。

## Python 接口风格

方法、参数和响应属性使用 `snake_case`；类名使用 `CapWords`。客户端通过关键字参数配置，取密、确认等操作直接传参，响应具有类型提示。使用 `with` 自动关闭 HTTP 会话：

```python
from jms_pam import Client

with Client(
    "https://jumpserver.example.com",
    app_id="<app-id>",
    app_secret="<app-secret>",
    instance_id="orders-worker-1",
) as client:
    credential = client.get_credential(key="<credential-key>")
    username = credential.account.username
    password = credential.account.secret
```

旧的 `jms_pam.credential.v1` 请求对象接口作为兼容入口保留，并发出 `DeprecationWarning`。新代码使用本页示例中的 `Client` 接口；升级时同步重新生成 SDK 接入配置。

## 内部架构与执行流程

Python SDK 管理 HTTP 会话、签名、事件读取和钩子。独立 Go Agent 入口为 `go/cmd/jms-pam-agent`，配置、交付、运行和本地接口位于 `go/agent`。本机规则选择模板、目标文件和有超时的服务或脚本动作；最新凭据、交付版本和显式业务生效确认分别持久化。

## 手动发起策略新周期

在凭据策略详情的“基本设置”或“事件接收”中点击“发起新周期”。发起后会打开新周期的时间线：

- 凭据变更订阅：为当前有应用授权的订阅账号重新发布 `credential.updated`，共用一个新的 `operation_id`。密码和版本不变，不生成改密开始、成功或失败事件。SDK 按事件 key 获取当前凭据；Agent 收到更新通知后也会重新取密，同版本不重复交付或重启服务。回执仅表示收到通知。离线客户端重连时通过快照获取当前凭据。
- 账号轮换：上一周期完成或取消后发起新周期。JumpServer 先验证备用账号能登录，再发布切换事件。客户端实际应用备用账号并确认；近期通过旧取密 API 使用过原主账号的应用，还需在切换后取得备用账号。与此同时，从切换时刻起观察原主账号的 JumpServer 取密记录；原主账号连续无成功取密达到配置时长（默认 7 天）才允许改密。期间再次取密会重置窗口。校验、切换、观察与改密共用一个周期。

管理 API：`POST /api/v1/accounts/application-credentials/<policy-id>/start-cycle/`，账号轮换需要策略修改和账号验证权限，返回 `credential` 和 `cycle_id`。策略停用、轮换未结束时不能发起新周期；订阅账号正在改密时须等待改密结束再重新发布。

## 手动发送应用事件

在应用列表的“更多 > 发送事件”，或应用详情的“事件处理 > 发送事件”中，选择事件类型、目标连接实例和有效期。

- `credential.switch.requested`：要求应用切换到策略当前发布的账号和版本。该请求不会更换策略的发布账号；更换发布账号应在轮换策略中操作。应用取密后必须校验请求中的账号和版本，完成连接切换并调用 `confirm_credential`，再回报成功。
- `application.restart.requested`：SDK 应用调用自己实现的重启处理函数，并在健康检查成功后回报结果。Agent 仅支持接入时配置为 EnvironmentFile + restart 的 systemd 服务，先重启，再检查服务状态。

WebSocket 的 `received` 回执表示收到请求，不表示执行成功。SDK 的 `execute_application_command(event, handler)` 会先向 Core 申请执行，只有 `accepted: true` 才调用处理函数；重复投递不会再次执行。处理函数正常返回后报告成功，异常则报告失败。应用自行负责处理函数中的业务幂等和健康检查。Agent 的账号切换请求在应用确认实际使用版本后才报告成功。

离线实例可在有效期内重新连接接收请求。无法使用 WebSocket 的 API 应用也可通过 AK/SK 签名轮询，使用固定的 `instance_id`；首次轮询会登记实例，之后管理员便可选择该实例发送事件：

1. `GET /api/v1/accounts/credential-client/commands/?instance_id=<instance-id>` 获取待处理请求（SDK 对应 `list_application_commands()`）。使用与凭据客户端相同的签名头，协议版本为 1。
2. `POST /api/v1/accounts/credential-client/command-result/`，提交 `instance_id`、`command_id` 和 `status: running`。只有响应 `accepted: true` 才执行。
3. 执行结束后向同一接口提交 `status: success` 或 `status: failed`；失败可附带不含敏感数据的 `error_code`。SDK 对应 `report_application_command_result()`。

请求超过有效期会显示超时，不能再申请执行。已申请执行的重启若因进程退出而无法回报，需检查应用状态后由管理员决定是否重新发送。普通旧取密 API 保持不变，仅调用取密接口不会接收手动事件。

## 选择接入方式

| 方式 | 适用场景 | 应用需要完成的工作 |
| --- | --- | --- |
| Python SDK | 应用可以修改 Python 代码并直接访问 JumpServer | 监听事件、拉取变化的凭据、切换连接并确认版本 |
| Go Agent | 不希望应用保存 JumpServer 密钥，或需要文件、EnvironmentFile、本地 Socket 交付 | 加载并验证 Agent 交付的凭据，再确认实际使用的版本 |

<!-- agent-doc:start -->

## Go Agent 接入

内置服务安装需要 Linux/root。从应用 Agent 接入向导下载 `jms_pam_agent.json`，构建或获取 Go 二进制，并使用稳定且唯一的实例 ID。Linux 服务配置为 `/etc/jms-pam-agent/agent.json`，服务名固定为 `jms-pam-agent`。

```bash
cd apps/accounts/clients/go
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
chmod 0600 ./jms_pam_agent.json
sudo /usr/local/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

macOS、非 root Linux 或 Windows 前台运行时，在向导中选择 JSON 或 Socket 交付，按照对应的 `init-local` 和 `run --local --config` 命令操作。只初始化一次，重启时复用生成的本机配置。前台模式以当前用户运行，不执行 systemd 动作；Windows 使用私有 ACL 而不是 POSIX 权限位。

`/etc/jms-pam-agent/agent.json`: `0600`; `state_file`, `event_file`, `delivery.delivery_root`, `delivery.socket_path`.

- JSON: `/opt/jumpserver-pam/credentials/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<credential-key>.env`
- Unix Socket: `/run/jms-pam-agent/agent.sock`

JSON 交付文件，EnvironmentFile 对接固定 systemd 服务，Unix Socket 提供本地 API。Agent 在交付成功后保存交付版本，应用验证并使用后才保存生效版本。Socket 归配置的应用用户所有，权限为 0600，本地请求应以该用户执行。

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<credential-key>.env
```

systemd unit 必须引用 EnvironmentFile。

本机 rules 配置目标文件、JSON/EnvironmentFile 或可信模板，以及可选的 systemd reload/restart 或固定可执行脚本。脚本通过标准输入接收凭据 JSON，参数固定、有超时，并应在验证业务生效后返回成功。Core 不能新增脚本路径或扩大本机能力。修改私有配置后重启 Agent。

身份只需要 app_id、app_secret、org_id 和稳定的 instance_id；应用授权控制 pull 范围，绑定策略控制 push 范围。文件路径和服务动作全部在本机配置：state_file 始终保留最新密码，event_file 追加不含密码的事件元数据，delivery 定义默认交付，rules 定义文件、模板及 reload/restart 或固定脚本。收到更新通知后主动取最新密码，先持久化，再原子替换文件，最后执行动作；交付失败会重试。规则使用 get_accounts 返回的 credentials[].key，订阅 push 的 key 为 account:<account-id>，不包含策略 key。rules 为空时默认按 key 写文件。

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


### 本地 API 与确认

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

交替轮换需要先验证真实连接、切换应用连接池并释放旧连接，再确认准确的 key、revision 和 account_id。凭据变更订阅无需确认，连接验证失败时不得确认。

```bash
/usr/local/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jms-pam-agent/agent.sock'
```

只有交替轮换需要 confirm。本地确认先持久化；confirmed 表示 Core 已接受，pending 表示之后重试。不能因为文件写入成功或服务重启就确认。

### 排查问题

```bash
sudo systemctl start jms-pam-agent
sudo systemctl status jms-pam-agent --no-pager
sudo journalctl -u jms-pam-agent -n 100 --no-pager
sudo systemctl restart jms-pam-agent
```

Agent 在启动、相关事件和每 300 秒进行同步。网络故障保留已获取的最新授权凭据；身份或授权被拒绝时阻断 Socket 取密，成功签名同步后恢复。已交付文件保留。SIGINT/SIGTERM 会关闭服务、连接和事件读取线程。

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Python SDK 完整接入

仓库另附两个可独立运行的文件配置 Demo：`file_apps.subscription` 和 `file_apps.rotation`。它们使用本节生成的 SDK 配置，接收事件后更新本地 JSON；运行命令和轮换确认条件见 [文件配置应用文档](file_apps/README.zh-hans.md)。

SDK 使用应用的 AK/SK，自动接收所有绑定到应用的有效策略。一条连接可同时处理订阅和轮换，接入向导提供按策略模式处理的通用示例。策略绑定变化自动生效。

### 接入前准备

1. 在“PAM 集成 > 凭据策略”创建“凭据变更订阅”或“账号轮换”策略并绑定应用。订阅策略明确选择要通知的账号；账号轮换当前选择同一资产上的两个账号。
2. 创建或打开目标应用，在“账号授权”页面授权应用可使用的资产账号。交替轮换必须授权策略中的两个账号。
3. 打开应用详情的“接入与连接实例”，点击“接入向导”，选择“SDK 接入”。
4. 生成并下载 `jms_pam_config.py`，使用向导中的示例代码。无需配置 ID 或策略列表。

向导会把生成的 `instance_id` 写入 `jms_pam_config.py`。容器重建时复用该文件以保持实例身份；多个副本应分别生成材料，或为每个副本设置稳定且不同的 `JMS_INSTANCE_ID`。

### 安装与配置

SDK 需要 Python 3.9 及以上。从 JumpServer 下载并解压 SDK 源码包后，在解压目录中使用应用实际运行的 Python 或虚拟环境安装：

```bash
python3 -m pip install .
```

将 `jms_pam_config.py` 放入应用可以导入的位置。该文件包含应用身份信息和生成的实例 ID，不要提交到代码仓库或输出到日志。

### 子类事件处理

需要维护账号映射、连接池等状态的应用可以继承 `Client` 并重写钩子方法。`__init__` 初始化本地状态；`watch_events()` 收到首次快照后，按策略类型取密，再调用 `on_credential_changed`。后续更新和重连快照也使用同一个钩子。

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


class MyClient(Client):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.credentials = {}

    def on_credential_changed(self, credential):
        # 验证新连接并切换应用连接池。
        raise NotImplementedError("请实现应用连接切换")
        # 切换成功后再保存：self.credentials[credential.key] = credential

    def on_credential_revoked(self, event):
        # 释放受影响的连接；随后的快照会重新核对完整授权范围。
        self.credentials.pop(event.get("credential_key"), None)


with MyClient(instance_id=instance_id, **client_options) as client:
    client.watch_events()  # 阻塞运行，事件交给子类钩子处理。
```

嵌入现有服务时使用 `start_events()`，启动后台监听后立即返回。`stop_events()` 停止监听并等待当前钩子结束，HTTP 客户端仍可使用。退出 `with` 或调用 `close()` 会停止事件流，等待钩子结束，再释放 HTTP 资源。每个客户端只允许一个钩子监听器；停止后可以重新启动。钩子内也可以停止或关闭自己的客户端。

读取线程和串行处理线程之间使用容量为 128 的有界队列。慢钩子不会立即暂停读取；队列满时产生背压。取密或 `on_credential_changed` 失败后按 1–30 秒指数退避重试，每次重新获取当前凭据。同一账号或 key 的新更新替换待重试项；快照重新确定重试范围，撤销或配置变更会清除待重试项，等待随后的快照。处理函数须支持重复调用；重连快照即使版本相同也可能再次触发钩子。

`on_event(event)` 在凭据钩子前观察原始事件，可处理快照状态核对、配置变更、生命周期事件及应用指令；指令仍须通过 `execute_application_command` 认领和上报。`on_credential_revoked(event)` 处理撤销。`on_event_error(error, event)` 接收错误，读取线程发生不可恢复错误时 `event=None`，默认只记录异常类型。原始事件和撤销钩子不会自动重试。完整快照状态核对示例见 `subclass_demo.py`。

`start_events()` 返回不代表首次凭据初始化完成；如果服务启动依赖凭据，可在子类中使用 `threading.Event`，完成初始化后再对外服务。后台钩子与主服务并行运行，共享业务状态须由应用按需保护。SDK 不会自动确认轮换，只有轮换策略的业务连接切换成功后才显式调用 `confirm_credential`。`clone()` 创建独立 HTTP 会话和全新的子类状态；子类构造函数有额外必填参数时须重写该方法。

原有 `watch_credential_events(stop_event=...)` 迭代器继续保留，回执、阻塞和取消语义不变。下面的示例仍使用原来的调用方式。

### 凭据变更订阅

管理员可以从应用管理查询账号 ID。已授权账号可以直接按 ID 取密：

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


with Client(instance_id=instance_id, **client_options) as client:
    response = client.get_credential(
        account_id="<account-id>",
    )
    password = response.account.secret
```

常驻应用监听凭据事件流；首次连接和重连快照也会提供当前账号：

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def fetch_credential(client, key):
    response = client.get_credential(key=key, allow_local_fallback=False)
    address = response.asset.address
    username = response.account.username
    secret_type = response.account.secret_type
    secret = response.account.secret
    # 使用新凭据更新应用连接；不要记录 secret。


with Client(instance_id=instance_id, **client_options) as client:
    for event in client.watch_credential_events():
        if event.get("event") == "snapshot":
            updates = event.get("credentials", [])
        elif event.get("event") == "credential.updated":
            updates = [event]
        else:
            continue
        for update in updates:
            account_id = update.get("account_id")
            key = update.get("credential_key") or update.get("key")
            if update.get("credential_mode") == "subscription" and account_id and key:
                if not key.endswith(f":{account_id}"):
                    key = f"{key}:{account_id}"
                fetch_credential(client, key)
```

订阅不需要 `credential_keys` 或 `confirm_credential`。生命周期事件只用于观察状态，不触发取密。

### 双账号交替轮换

事件快照提供每条轮换策略的唯一 Key。收到首次快照时获取当前账号，收到更新或重连快照后再次取密；只有应用验证新连接并切换成功后才能确认：

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def apply_credential(credential):
    raise NotImplementedError("请实现连接验证、连接池切换和旧连接释放")


def switch_credential(client, key):
    response = client.get_credential(key=key, allow_local_fallback=False)
    apply_credential(response)
    client.confirm_credential(
        key=response.key,
        revision=response.revision,
        account_id=response.account.id,
    )


with Client(instance_id=instance_id, **client_options) as client:
    for event in client.watch_credential_events():
        if event.get("event") == "snapshot":
            updates = event.get("credentials", [])
        elif event.get("event") == "credential.updated":
            updates = [event]
        else:
            continue
        for update in updates:
            key = update.get("credential_key") or update.get("key")
            if key and update.get("credential_mode") == "alternating_rotation":
                switch_credential(client, key)
```

`Account.secret` 是密码或密钥内容，具体类型由 `Account.secret_type` 标识。不要把密码或认证请求头写入日志。

### 完成一次凭据轮换

1. 在“PAM 集成 > 凭据策略”中点击“发起新周期”。JumpServer 先验证备用账号可登录，成功后发布账号切换及 `credential.updated`。
2. 应用按事件中的 key 调用 `get_credential`，使用备用账号建立并验证连接，切换成功后调用 `confirm_credential`；生命周期事件只记录状态，不触发取密。
3. 等待所有参与实例确认，同时从切换时刻起观察原主账号的 JumpServer 成功取密记录。原主账号每次再次取密都重置无取密窗口；达到配置时长（默认 7 天）后才进入可改密状态。
4. 创建并执行原主账号的改密任务；执行前再次核对客户端确认和无取密窗口。
5. 检查改密结果；成功后轮换完成，当前账号保持不变，下一轮按相反方向切换。

### 应用指令

使用 `list_application_commands()` 轮询待处理请求，通过 `execute_application_command(event, handler)` 认领并执行。只有认领成功才调用 handler。切换请求须校验请求中的账号和版本，验证连接并应用凭据后再确认；重启请求须完成重启和健康检查后才能返回。handler 抛出异常会上报失败，上报结果失败也会保留原始业务异常。

### SDK 常用方法

同步客户端提供以下常用方法：

- `get_credential`：按应用授权账号 pull 使用 `account_id`；push 订阅使用 `key=account:<account-id>`，交替轮换使用策略 key。必须且只能提供一种选择参数。
- `confirm_credential`：仅用于交替轮换，确认应用已经验证并使用指定 revision。
- `watch_events` / `start_events` / `stop_events`：前台或后台运行子类钩子，并停止监听。
- `watch_credential_events`：阻塞监听凭据事件和重连快照。
- `list_application_commands` / `execute_application_command`：轮询、认领和上报应用指令。
- `sync_agent`：使用 `KnownRevision` 对账保留版本和已交付版本。
- `clone`：创建独立 HTTP 会话；`close` 或 `with` 语句释放会话和事件流。

SDK 在将业务事件交给调用方前自动尽力发送接收回执。回执仅表示 SDK/Agent 已读取该事件，不表示已取密或应用凭据，也不能代替 `confirm_credential`；回执发送失败不影响事件处理。已有 SDK/Agent 部署需要更新并重启后才能上报回执。重连快照用于恢复当前凭据版本，不会重放历史事件或补报历史回执。

连接在线状态由 WebSocket Ping/Pong 维护，不再提供 HTTP 心跳接口。应用只需保留低频版本对账作为恢复路径。

HTTP、鉴权、网络和响应解析错误统一抛出 `jms_pam.PAMError`。业务重试边界可以读取 `code`、`status_code`、`detail` 和 `original_error`。日志中不要记录凭据或认证请求头。

### 最新凭据与后端不可用

取密始终先请求 API。成功获取新凭据后替换本地保留值，更旧版本不会覆盖已获取的新版本；保留值不按时间过期。只有 API 超时、网络故障或 HTTP 5xx 时，才返回相同查询条件下已获取的最新凭据，并设置本地来源标记。首次获取失败且没有保留值时，抛出原始错误。SDK 在当前客户端内存中保留这些值，直到更新、撤销或关闭；clone 和进程重启从空状态开始。Agent 通过已有受保护的本地状态保留最新凭据。HTTP 401/403/404、client_upgrade_required 清空 SDK 的保留值并报错，成功响应格式错误也会报错。明确撤销删除相应凭据，push 快照移除订阅范围外的 push 项；配置变更通知先保留已有值，由后续快照核对授权范围。Agent 在 HTTP 同步前先执行明确撤销或快照授权范围缩小并保存范围，后端故障期间或重启后也会阻止相应本地取密。credential_not_found（HTTP 400）同样清除 SDK 保留值。 按 account_id 直接 pull 始终需要实时 API 响应；push 快照不能证明缓存的 pull 凭据仍获授权。

- `credential.from_local`
- `get_credential(key=..., allow_local_fallback=False)` / `get_credential(account_id=..., allow_local_fallback=False)`

启用高层事件监听后，snapshot、credential.updated 会自动获取当前凭据并替换本地保留值，再调用业务处理函数。刷新失败时保留上一份凭据并重试。Agent 同样在更新通知后主动取密，后端故障期间保留已有凭据。事件刷新和手动切换使用下方必须实时获取的调用；保留的密码不能被当成刚获取的新版本，也不会自动确认轮换。

事件连接空闲时每 10 秒发送应用层 ping，约 30 秒收不到消息则重连。重连采用 1–30 秒指数退避并重新签名。重连快照恢复当前状态，不重放历史事件。

<!-- sdk-doc:end -->

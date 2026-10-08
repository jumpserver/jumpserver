# Go jms-pam-agent

Agent 是独立 Go 二进制，运行时不依赖 Python。内置 systemd 安装仅支持 Linux/root；Linux、macOS 和 Windows 可由当前用户前台运行。Linux 服务使用本机私有配置 `/etc/jms-pam-agent/agent.json`。

```bash
systemctl start jms-pam-agent
systemctl status jms-pam-agent
systemctl restart jms-pam-agent
journalctl -u jms-pam-agent
```

服务固定为 `jms-pam-agent.service`。身份使用应用 AK/SK 和稳定的 `instance_id`。应用授权账号决定按需 pull 范围；应用绑定的凭据策略决定主动同步和推送范围。每个业务副本使用稳定、唯一的 `instance_id`。

新建应用或修改账号授权时，可以选择具体账号、全部账号或按属性选择账号。匹配的账号数受系统全局上限约束，默认 10 个；在 Core 的 `config.yml` 中通过 `APPLICATION_ACCOUNT_SCOPE_LIMIT` 调整，修改后需重启 Core。已有授权在修改账号范围前保留原有取密能力。新授权的动态范围日后超过上限时，账号列表与取密请求会失败，直到缩小范围或调高上限；服务端不会任意截取前 10 个账号。保存新范围后，Agent 按下一次同步结果撤销不再授权的账号 push key。

## 安装

在仓库的 `apps/accounts/clients/go` 或下载的 Go SDK 源码目录构建。构建需要 Go 1.23+；目标 Linux 主机只需要二进制和 systemd。

```bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
# ARM64 主机使用 GOARCH=arm64。
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
sudo /usr/local/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id orders-node-1
sudo systemctl start jms-pam-agent
```

引导文件从应用接入向导下载，包含 AK/SK。安装时通过签名同步获取并固定交付能力，配置写入 `/etc/jms-pam-agent/agent.json`，最新凭据和运行状态写入 `/var/lib/jms-pam-agent/state.json`，均为 `0600`。安装启用并启动固定服务；重复安装核对身份，不更换已有身份。构建产物需要匹配目标架构。

## 运行流程

`更新通知 / 首次及重连快照 → 签名核对授权与版本 → 实时取密 → 保存最新凭据 → 渲染并原子替换文件 → 执行动作 → 保存交付版本`

- 默认按 key 写 JSON 文件，也支持 EnvironmentFile 和 Unix Socket。默认目录及 socket 路径由本机文件指定，具体值在本机 `delivery` 中。
- 本机 `rules` 可以指定其他服务的配置路径、可信模板，以及 reload/restart 或固定脚本。
- 同一版本成功交付后跳过重复动作；初次交付、新版本和失败重试执行动作。通知仍会主动取密。
- 获取或交付失败按 1–30 秒指数退避重试，并每 300 秒对账。读取器使用有界队列，业务动作串行执行；WebSocket 心跳与重连由 Go SDK 管理。
- 最新成功获取的密码不按时间过期，刷新失败不丢失，Agent 重启可恢复。更旧的 API 响应不会覆盖新版本。
- 明确撤销或授权快照缩小会先停用相应本地取密并保存范围，再尝试 HTTP 同步；HTTP 身份拒绝阻断本地访问。已写入业务文件不会因网络错误被删除。
- `received`、保存最新值、文件交付和业务生效分别记录。文件写入、脚本退出或服务重启本身不会确认轮换；只有本机 `application_check` 显式配置 `confirm_on_success` 且成功验证运行中的应用，Agent 才确认准确版本。

## 本机配置

下载文件就是完整的本机配置，安装时仅设置稳定的实例 ID。以下示例替换应用身份和业务路径后即可使用；不需要在后端管理接入配置。`rules` 是本机管理员配置，Core 不能通过事件添加脚本、参数、目标文件或扩展已固定的交付能力。

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
  "rules": [
    {
      "keys": ["orders-db"],
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
}
```

`orders-db` 是轮换策略 key 的示例。订阅 push 的凭据 key 为 `account:<account-id>`，与选中账号的策略无关；多条策略命中同一账号也只交付一份。先运行 `get_accounts`，复制输出的 `credentials[].key` 到规则和模板。业务文件可在本机 `rules.files.path` 指定可读的固定路径。

从旧版 `策略 key:账号 ID` 升级时，首次成功在线同步会取得新 key，清理 Agent 状态里的旧订阅项。未配置自定义 `rules` 时还会删除当前交付目录中的旧默认文件。使用自定义规则的主机需在重启前把 `rules.keys` 和模板中的旧 key 改成 `account:<account-id>`；自定义目标文件及曾使用过的交付目录需要单独检查。

`rules` 为空或省略时，默认 JSON 模式写 `delivery_root/<key>.json`；`state_file` 始终保留最近成功获取的密码。

`keys` 可指定多项凭据，使脚本或完整配置模板获得同一交付快照。显式配置 `rules` 时，每个待交付 key 都必须被规则覆盖；多项规则应支持重试。文件格式支持 `json`、`environment`、`template`；EnvironmentFile 规则限一项凭据。单项 JSON 输出扁平凭据，多项 JSON 输出按 key 组织的对象。

这里的 `rules[].keys` **是 JumpServer 下发凭据的标识列表**，不是业务配置中的 `DB_USER`、`DB_PASSWORD`，也不是数据库用户名。它只回答“这条规则使用哪几份凭据”；`config_update` 的模板或脚本才决定“把用户名和密码写到哪些配置字段”。在 `jms-pam-agent get_accounts` 输出中，找到所需账号的 `credentials[].key` 后填入这里：普通订阅通常是 `account:<账号 ID>`；A/B 双账号轮换是一个固定的策略 key（例如 `cred-...`），切换 A→B 时 key 不变，凭据中的 `account_id`、`username` 和 `secret` 更新。若主库和报表库同时使用，规则列出两个不同的 key；若 A/B 只是同一主库连接的交替账号，规则只列出一个轮换 key。

新配置推荐使用 `rules[].accounts`，按实际使用的账号 ID 声明规则，不用在 Agent 配置中保存策略 key。轮换账号设置 `allow_account_switch: true`；Core 在事件、首次连接快照、同步结果和凭据响应中提供 `account_switch.account_ids`。只要声明的账号属于该轮换组，Agent 就使用这条规则，并写入本次生效账号的用户名和密码。A→B、B→A 以及首次接入时已在 B 都复用同一规则。`allow_account_switch` 按账号设置，因此同一文件可同时使用轮换账号和普通订阅账号：

```json
{
  "accounts": [
    {"account_id": "<主库账号 A ID>", "allow_account_switch": true},
    {"account_id": "<报表库账号 ID>"}
  ],
  "config_update": {
    "targets": ["/etc/order-service/database.yml"],
    "script": {"type": "script", "path": "/usr/local/libexec/jms-pam/update-business-config"}
  },
  "service_action": {"type": "script", "path": "/usr/local/libexec/jms-pam/recreate-business"},
  "application_check": {
    "type": "script", "path": "/usr/local/libexec/jms-pam/check-running-business",
    "confirm_on_success": true
  }
}
```

脚本的 `credentials` 对象以**本机声明的账号 ID**为键；轮换后该项的 `account_id` 是实际生效账号 B。模板和脚本无需改索引。Agent 会向 Core 申报这些账号，只接收相关策略；轮换进行中不能通过删除本机规则退出该轮换。若多个策略同时匹配同一账号规则，或缺少轮换组信息，交付失败且不会确认。旧 `keys` 规则继续支持，但同一条规则不能混用 `keys` 和 `accounts`。

### 分阶段适配业务配置

新规则可将职责分成四个本机配置块。执行顺序为 `credential_check → config_update → service_action → application_check`。检查脚本和更新脚本都从 stdin 接收同一份按 key 组织的凭据 JSON。`config_update` 选择 `files`（完整文件模板/JSON/EnvironmentFile）或 `script`（定点修改现有配置），不能同时设置。`service_action` 支持固定脚本或 systemd reload/restart；两个检查块只接受固定脚本。旧规则的 `files`/`action` 仍可继续使用，但不能和新块混用。

例如同一应用同时使用主库和报表库账号，且两个账号写入同一个配置文件：

```json
{
  "keys": ["<primary-key>", "<report-key>"],
  "credential_check": {
    "type": "script", "path": "/usr/local/libexec/jms-pam/check-db-login"
  },
  "config_update": {
    "targets": ["/etc/order-service/database.yml"],
    "script": {"type": "script", "path": "/usr/local/libexec/jms-pam/update-business-config"}
  },
  "service_action": {
    "type": "script", "path": "/usr/local/libexec/jms-pam/recreate-business"
  },
  "application_check": {
    "type": "script", "path": "/usr/local/libexec/jms-pam/check-running-business",
    "confirm_on_success": true
  }
}
```

把这条规则放入 `rules` 数组。脚本更新必须声明 `targets`，以检查同一文件是否被多条规则占用；脚本实际写入范围仍由本机管理员负责。四个脚本由本机管理员提供，路径和参数不能由 Core 事件改变。`credential_check` 应使用新账号实际连接目标数据库，失败时不修改文件；`config_update` 应仅修改绑定字段并保留其他账号与设置；`service_action` 应让业务重新读取配置；`application_check` 应验证运行中的业务已经用新账号完成数据库操作。脚本非零退出会阻止该版本完成交付并触发重试。更新或启动失败后的配置回退由本机脚本负责，Agent 不会自动回滚业务文件。

同一目标文件只能属于一条规则；多个账号共用文件时应放在同一 `keys` 中，以最新可用凭据快照更新一次。缺少任何必需 key 时，Agent 不会运行此规则。`confirm_on_success` 只对轮换 key 生效，且该 key 的每条规则都必须通过应用检查并显式开启，才会持久化准确版本的生效确认；Core 暂不可用时稍后重报。不要用单纯的进程存活检查冒充业务连接验证。JumpServer installer 的 `config.txt` 需用更新脚本定点修改 `DB_USER`/`DB_PASSWORD`，并重建读取环境变量的 Core、Celery 容器；直接使用 `config.yml` 的部署应更新对应 YAML 字段并重启实际读取它的进程。两种场景均需独立验证新账号和切换后的真实数据库连接。

本机模板 `/etc/jms-pam-agent/orders-db.tmpl`：

```gotemplate
{
  "address": {{json (index .Credentials "orders-db").Address}},
  "username": {{json (index .Credentials "orders-db").Username}},
  "password": {{json (index .Credentials "orders-db").Secret}}
}
```

`json` 函数完成 JSON 转义。其他业务格式需要使用该格式正确的转义规则，复杂更新可交给脚本。所有文件先渲染成功才开始写入，逐文件原子替换；多文件和后续动作不构成一个事务。动作失败时保留最新凭据，交付版本不前进，之后重试。

更新本机配置后：

```bash
sudo chmod 0600 /etc/jms-pam-agent/agent.json
sudo jms-pam-agent check-config
sudo systemctl restart jms-pam-agent
```

EnvironmentFile 更新需要应用重新读取配置。systemd `reload` 不会替换运行中进程的环境变量；只读取启动环境的服务应选择 `restart`。systemd 动作完成后会检查服务是否 active；应用层数据库连接是否切换仍由应用验证。

## 复杂场景使用脚本

替换规则中的 `action`，也可以省略 `files`，由脚本负责更新完整配置：

```json
{
  "type": "script",
  "path": "/usr/local/libexec/jms-pam/apply-orders",
  "args": ["--config", "/etc/order-service/database.json"],
  "timeout_seconds": 60
}
```

Agent 直接运行固定可执行文件，不拼接 shell 命令。脚本通过标准输入接收 JSON：

```json
{
  "event": "credentials.updated",
  "credentials": {
    "orders-db": {
      "key": "orders-db",
      "revision": 3,
      "username": "orders",
      "secret": "<latest-password>"
    }
  }
}
```

实际凭据还包含账号、资产、地址等字段。密码不放进参数、环境变量或 Agent 日志。脚本自身也应避免输出密码；Agent 丢弃脚本 stdout/stderr。退出码 0 表示动作完成，非零或超时进入重试。脚本必须先验证配置、完成 reload/restart 和健康检查，再返回成功，并支持重复执行。默认超时 120 秒，上限 300 秒；超时或服务停止会终止脚本进程组。

服务、模板、脚本和目标文件的父目录必须由 root 管理，不允许组或其他用户写入，也不允许符号链接。脚本必须是本机可信普通可执行文件，不允许 setuid/setgid。交付文件为 `0600`，按规则 owner 或配置的 app_user 设置归属；Core 无法扩大这些本机执行能力。

## 本地 API 与生效确认

Socket 归 `app_user` 所有，权限 `0600`，父目录为 root 管理的 `0750`。按本机 `delivery.socket_path` 请求：

```bash
curl --unix-socket '<socket-path>' http://localhost/v1/health
curl --unix-socket '<socket-path>' http://localhost/v1/credentials/orders-db
jms-pam-agent confirm orders-db --revision 3 --socket '<socket-path>'
```

应用验证真实连接并成功切换后，才确认准确版本：业务可通过本机接口显式确认，也可使用通过检查脚本验证的 `confirm_on_success`。同步运行的检查脚本不应反向调用 Agent 的确认接口。交替轮换需要确认，凭据订阅无需确认。确认先持久化，Core 不可用时返回 `pending` 并重试；Core 接受后为 `confirmed`。手动切换指令只在相应版本已确认生效后报告成功。重启指令只操作本机已经固定为 restart 的 systemd 服务。

旧 Python Agent 和旧配置格式已移除。修改旧安装时先停止旧进程，按新格式重新生成配置并完成在线同步，再接管交付位置；旧状态不自动转换。

## CLI 查询账号和凭据

CLI 通过正在运行的 Agent 的私有 Unix Socket 查询，复用它的身份、授权和持久化状态：

```bash
jms-pam-agent get_accounts
jms-pam-agent get_secret '<account-id>'
# 自定义配置或直接指定应用用户可访问的 Socket：
jms-pam-agent get_accounts --config /path/to/agent.json
jms-pam-agent get_secret '<account-id>' --socket '<socket-path>'
```

也支持 `get-accounts` / `get-secret`；旧命令 `get_credential` / `get-credential` 仍可用。`get_accounts` 不取密码，列出应用授权 pull 的账号和资产；未订阅 push 的账号也会列出，其 `credentials` 为空。策略只显示主动同步范围，轮换策略只标注当前生效账号。`get_secret ACCOUNT_ID` 直接在线核对应用授权并按需取密，不要求账号绑定凭据策略，也不会把仅 pull 的密码写入 Agent 的持久化状态。账号列表 API 支持 `limit`、`offset` 和 `search`。

`--config` 可以使用相对当前工作目录的路径，例如 `--config subscription/agent.json`。加载后仍检查私有权限和符号链接；配置内容中的状态、Socket、交付文件等路径必须为绝对路径。CLI 失败时显示具体的本机检查原因或 HTTP 状态，不输出后端错误正文。

输出为 JSON，`source` 为 `api` 或 `local`。只有网络错误、超时或 HTTP 5xx 才允许返回仍授权的 push 凭据缓存；仅 pull 的凭据在离线时不可用。授权拒绝、撤销、错误响应和版本回退都返回失败。离线账号列表仅包含已经保留凭据且仍授权的账号。取密命令会将密码输出到 stdout，Agent 自身日志和事件文件不会记录密码。查询不会上报业务生效确认。

## Linux / macOS / Windows 前台运行

本地开发无需 root 或 systemd。先从现有应用的 Agent 接入向导下载引导 JSON，设置 `0600`，选择 JSON 或 Socket 交付。在 Go SDK 目录执行：

```bash
go build -o jms-pam-agent ./cmd/jms-pam-agent
chmod 600 /private/path/jms_pam_agent.json
./jms-pam-agent init-local \
  --bootstrap /private/path/jms_pam_agent.json \
  --directory "$HOME/.jms-pam-agent/orders" \
  --instance-id local-orders-agent
./jms-pam-agent run --local --config "$HOME/.jms-pam-agent/orders/agent.json"
```

Windows 从 Go SDK 目录构建 `GOOS=windows GOARCH=amd64 go build -o jms-pam-agent.exe ./cmd/jms-pam-agent`，然后在引导文件所在目录用 PowerShell 运行：

```powershell
$agentDir = Join-Path $HOME 'jms-pam\orders'
.\jms-pam-agent.exe init-local --bootstrap (Join-Path $PWD 'jms_pam_agent.json') --directory $agentDir --instance-id $env:COMPUTERNAME
.\jms-pam-agent.exe run --local --config (Join-Path $agentDir 'agent.json')
```

Windows 需要支持 AF_UNIX 流套接字。

`init-local` 通过签名同步确认现有应用范围，生成当前用户的本机路径；只需初始化一次，后续启动复用 `agent.json`。Windows 的引导文件与凭据路径须位于当前用户主目录下，并具有私有 ACL；Agent 拒绝链接和重解析点。本地 Socket 路径需短于 108 字节。Windows 默认凭据文件名使用 key 的 SHA-256 哈希，JSON 内容仍保留原 key。前台模式使用应用授权范围和本机交付规则，支持 JSON 或 Socket，拒绝 EnvironmentFile 与 systemd 动作；Windows 可信脚本动作仅接受 `.exe`。模板、脚本和显式文件规则需自行指定受保护的本机路径。Linux 生产服务仍使用固定 `systemctl start jms-pam-agent`。

目录中：

- `agent.json`：身份及本机规则。
- `events.jsonl`：追加事件元数据，包括 `received`、`saved`、`delivered` 阶段和 UTC 时间；不含密码。
- `credentials/<key>.json`：默认 JSON 模式原子替换的最新密码及账号、版本信息。
- `state.json`：最新成功取密值、授权、交付和确认状态，支持离线重启。
- `run/agent.sock`：CLI 和应用的本地访问入口。

以上配置、事件和凭据文件均为 `0600`。生产配置也可以设置可选的绝对路径 `event_file`，该路径必须与状态和凭据交付文件分开。事件日志是本机观察记录，不提供后端历史事件重放或恰好一次保证。写文件不代表真实服务已切换连接；这个简单示例不会自动确认轮换。

在另一个终端查询：

```bash
./jms-pam-agent get_accounts --config "$HOME/.jms-pam-agent/orders/agent.json"
./jms-pam-agent get_secret '<account-id>' --config "$HOME/.jms-pam-agent/orders/agent.json"
```

## 本地验证

```bash
go test -race ./agent
go build ./cmd/jms-pam-agent
```

单测验证文件渲染、原子替换、脚本标准输入和超时、更新取密、离线重启、撤销、失败重试、生效确认与 Socket 生命周期。Linux systemd 安装和真实业务 reload/restart 应在目标主机验证。

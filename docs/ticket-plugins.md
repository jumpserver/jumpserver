# PAM 工单类型插件

审批引擎继续负责流程、任务、状态和时间线。每个业务类型在 `apps/tickets/plugins/<type>/` 中提供 `plugin.py`，启动时自动发现 `Plugin` 类。类型标识必须唯一且保持稳定；这是一套随应用代码发布的扩展方式，不支持上传代码或运行时安装。

## 本次范围

| 类型 | 申请方式 | 审批完成后的行为 |
| --- | --- | --- |
| `apply_asset` 资产授权 | 用户申请 | 按冻结的资源、账号、动作、有效期和授权用户创建权限 |
| `login_confirm` 系统登录复核 | ACL 触发 | 原登录入口读取审批结果 |
| `login_asset_confirm` 资产登录复核 | ACL 触发 | 激活原连接令牌 |
| `command_confirm` 命令复核 | ACL 触发 | 原命令入口读取审批结果 |
| `view_secret` 查看账号密码 | 用户申请或账号页操作触发 | 按账号、申请人和组织创建限时查看授权；在工单详情按需取密 |
| `file_transfer` 文件上传下载 | 用户申请 | 仅审批与留痕 |
| `download_replay` 录屏下载 | 用户申请 | 仅审批与留痕 |
| `change_secret` 账号改密 | 用户申请 | 仅审批与留痕 |

`view_secret` 已接入授权 handler 和专用取密 API；审批时不读取或保存密码。`file_transfer`、`download_replay`、`change_secret` 尚未接入执行 handler，也未改变现有业务 API 的权限。后续按业务逐类接入，不能把 approved 直接解释为操作已经执行。

`applicant` 始终是实际提交者。资产授权插件使用 `request_data.apply_users` 保存单个授权用户 UUID 的列表，省略时默认申请人自己。代他人申请需要本组织的 `tickets.apply_asset_for_others` 权限，并且选用的流程每条路径都必须经过组织管理员审批。申请人和授权用户都不能审批该工单，包括转交和加签。受理前后均检查组织和用户有效性；`@USER` 的上下文和授权校验针对授权用户。旧工单没有该参数时仍给原申请人授权。历史多人授权工单保持原有快照和授权，不重新执行。

授权用户通过 `TicketBeneficiary` 关联查询自己的工单和流程实例，并在工单结束时收到结果通知。原 `applicant` 保留发起人、撤回人和审计身份；`applicant_manager` 始终是发起人的直属负责人，代申请需要的组织管理员使用 `org_admin` 审批人解析器。

工单公共字段 `origin` 记录创建入口，与类型、执行模式和审批结果分开：用户经申请 API 提交为 `manual`，ACL 等业务入口为 `system`。账号页操作入口提交 `view_secret` 时也标记为 `system`。插件元数据的 `creation_modes` 声明支持 `manual` 和/或 `operation`；同一个类型可以同时支持两种来源，不能按类型推断来源。历史登录、资产连接和命令复核工单在迁移中标记为 `system`。我发起的列表按来源切换，默认只显示进行中，已完结和全部可通过状态筛选查看。

工单和运行中的流程实例以 `org_id` 记录业务归属；普通用户申请必须选择一个具体组织，资源、授权用户、审批人和权限检查都以该组织为准。流程定义可以放在根组织供各组织复用，但实例仍属于提交工单的组织。系统登录复核插件的 `allow_global` 是显式例外。个人的“我发起的／待我审批／为我申请”列表汇总本人在各组织的相关工单，详情中的组织名称和审批操作所带的 `oid` 用于识别、切换工单归属；审计工单列表则按当前组织筛选，根组织可查看全部。

## 增加一个类型

新增目录和 `__init__.py`，然后实现 `plugin.py`。可把简单参数 Serializer 放在同目录的 `serializer.py`：

```python
# plugins/example/serializer.py
from rest_framework import serializers
from tickets.plugins.resources import RequestSerializer


class Parameters(RequestSerializer):
    reason = serializers.CharField(max_length=1024, label='申请原因')
```

```python
# plugins/example/plugin.py
from django.utils.translation import gettext_lazy as _
from tickets.plugins.base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'example'
    label = _('Example request')
    self_service = True
    request_serializer = 'tickets.plugins.example.serializer.Parameters'
```

这样即可使用统一接口和前端申请页，不必新增 TicketType 枚举成员、模型、迁移、ViewSet 或 URL。点击“申请工单”会从 `/ticket-types/` 加载可自助申请的类型，在抽屉中选择后打开对应表单；新增类型自动出现在抽屉中。表单支持文本、列表、选项、整数、日期及资产选择。复杂表单仍可编写专用组件；当前资产授权保留专用表单，数据统一保存在 `Ticket.request_data`。

插件发现期间不要导入模型或 Serializer，使用字符串路径及方法内导入，避免 Django 初始化循环。注册表检测重复或非法标识并阻止启动。移除插件前应处理历史工单和在途实例，不能直接删除仍被引用的类型。

### 插件接口

- `type`、`label`：类型标识和名称。
- `self_service`：是否允许用户从统一申请入口提交；系统复核类型为 false。
- `creation_modes`：插件支持的创建入口；`manual` 是统一申请页，`operation` 是业务操作触发。仅供入口展示与能力声明，服务端仍校验具体资源和流程。
- `request_serializer`：校验类型参数，包含资源范围及申请资格检查。继承 `RequestSerializer` 可拒绝未声明字段，密码和私钥等敏感值不进入申请数据。
- `build_context(ticket)`：构建审批条件需要的服务端快照。默认把参数置于 `context.request`，公共代码固定申请人和请求类型。资产/账号条件可复用 `snapshot_assets` 及 `account_context`。
- `validate_submission(ticket, context)`：提交工作流前校验该类型自己的流程约束；资产代申请在这里复核每条路径都有组织管理员审批。
- `filter_workflow_options(request, org_id, workflows)`：筛选申请页可选择的已发布流程；资产代申请在这里检查权限并筛选流程。真正的提交校验仍由 Serializer 和 `validate_submission` 执行。
- `excluded_approver_ids(context, applicant_id)`：补充该类型禁止审批的用户；公共层另按节点的 `exclude_applicant` 配置排除申请人，并在创建任务、审批、转交和加签时统一使用。
- `notify_processed(ticket, processor)`：发送该类型的额外结果通知；资产授权在这里通知授权用户。
- `allow_direct_approval(ticket)`：控制通知中的直接审批链接是否可用。
- `on_approved(instance, ticket)`：可选。默认无操作；自动执行的插件显式声明 `execution_mode = 'automatic'`，成功后返回事件数据，框架才记录 `action.executed`。读取 `instance.context`，不重新读取可变的申请参数作为授权依据。
- `get_available_actions(ticket, user)`：可选。详情页当前用户可用的工单动作；每次读取时检查授权、对象和时效，动作 API 再次独立校验。
- `get_result_resources(instance, event, user)`：可选。展示业务动作产生的对象，默认读取事件中的 `resources` 快照并返回纯文本；插件可增加本地化 `label` 和当前用户有权访问的站内 `url`。统一活动列表直接渲染，无需按工单类型增加前端分支。
- `execution_mode = 'external'`：由现有业务入口消费审批结果，例如登录和命令复核。

### 业务结果与详情跳转

`on_approved()` 可在原返回值中增加 `resources` 数组，支持一次操作产生多个对象。每个对象保存稳定的 `type`、字符串 `id` 和执行时的 `name`；不保存凭据或有时效性的访问链接。例如资产授权返回：

```python
return {
    'action': ticket.type,
    'ticket': str(ticket.pk),
    'resources': [
        {'type': 'asset_permission', 'id': str(permission.pk), 'name': permission.name},
    ],
}
```

事件 API 保留原 `data`，另返回经过 `get_result_resources()` 处理的只读 `resources`。插件在读取时以 `instance.org_id` 检查查看权限和对象是否存在，再添加 `/ui/#/...` 格式的详情地址，并带上 `oid`。不要使用可能已缓存了其他组织权限的 `user.perms` 来作跨组织判断。链接只影响展示，目标详情 API 仍执行原有权限校验。

资产授权插件已接入：活动中的“业务动作完成”下面展示授权名称，有 `perms.view_assetpermission` 权限且规则仍在原组织时可在新标签页打开详情。无权限、规则被删除或移到其他组织时保留执行时名称，不提供链接；后续改名不改变事件快照。旧事件没有 `resources` 时，只通过工单 ID 查找现存且标记为 `from_ticket` 的规则，使用其当前名称展示，不重放授权、不改写历史；规则不存在时仍显示原来的完成事件。

handler 在实例锁和审批数据库事务内执行。数据库内的授权可直接完成；远程任务复用业务模块现有的任务提交及幂等机制，不能在这里阻塞等待远程执行，也不能将任务已提交标记为远程执行成功。没有 handler 的类型保持 `approval_only`。

新类型的资源对象归属、操作权限、审批排除规则以及后续执行资格由该插件/业务模块负责；组织成员身份、流程类型匹配和工作流调度由公共层校验。录屏申请只允许自己的会话或有会话查看权限的人请求本组织会话；账号类申请遵循现有可申请资产范围配置，只接受该资产上真实存在的账号名。

## API

以下路径均以 `/api/v1/tickets/` 开头。

- `GET ticket-types/`：类型名称、申请方式、执行模式和参数描述。
- `POST tickets/open/`：统一申请入口。
- `GET ticket-types/apply_asset/options/?org_id=...&search=...`：本组织有效授权用户选项。
- `GET workflows/options/?type=apply_asset&org_id=...&beneficiary=...`：代申请时只返回每条路径均有组织管理员审批的流程。
- ACL 入口继续可用；资产申请与三类复核工单的专用 API 已并入 `tickets/open/` 和 `tickets/{id}/`。资产富表单从 `OPTIONS tickets/?type=apply_asset` 获取字段描述。
- 工单读取结果新增 `request_data`、`request_items`、`execution_mode` 和只读 `origin`，列表可用 `origin=manual|system`、`status=open|closed` 筛选；审批任务、撤回、评论等 API 不变。
- `GET /api/v1/accounts/accounts/{account_id}/request-secret-ticket/`：账号页获取本组织可选的已发布密码查看流程。
- `POST /api/v1/accounts/accounts/{account_id}/request-secret-ticket/`：传 `workflow_id`、`duration` 和可选 `comment`，创建 `origin=system` 的 `view_secret` 工单并返回工单 ID。服务端从账号对象确定资产、用户名和组织，不接受客户端指定授权对象。
- `POST /api/v1/accounts/accounts/{account_id}/reveal-by-ticket/`：传 `ticket_id`；仅审批通过、未过期、未撤销授权的申请人可读取该账号**当前**密码。响应禁止缓存，读取写审计事件和操作日志。

```json
{
  "type": "view_secret",
  "title": "排障查看账号密码",
  "org_id": "组织 UUID",
  "workflow_id": "同类型已发布启用流程 UUID",
  "request_data": {
    "asset": "资产 UUID",
    "accounts": ["root"],
    "duration": 600
  }
}
```

资产授权在 `request_data` 内填写原 `apply_assets`、`apply_accounts`、`apply_actions`、日期等字段以及可选 `apply_users`（只能有一个 UUID）。申请人不能通过传入别人的 applicant 来代申请，应填写 apply_users。执行模式随提交上下文冻结，升级 handler 不会让已经提交的 approval_only 工单开始自动执行，也不会把历史审批工单展示成已自动执行。

`view_secret` 审批完成后，handler 只创建数据库中的 `TicketSecretAccess` 授权，绑定工单、账号 UUID、申请人、组织与过期时间。详情的 `available_actions` 只向符合条件的申请人展示查看按钮；点击时专用账号 API 重新检查工单状态、授权时效、组织成员、账号有效性及全局禁止查看密码配置。若启用了查看密码 MFA 设置，专用 API 仍要求 MFA。密码从当前账号读取，不写入工单、事件、缓存或访问链接；审批后轮换密码时读到的是新密码。授权记录是唯一的权威状态，未来可加短时缓存加速，但撤销、过期和全局禁止策略必须保持实时有效。

`tickets.0016_merge_ticket_models` 将四种旧多表继承工单的业务字段和关联 UUID 搬入通用 `request_data`，再删除子表。连接令牌的 `from_ticket` 先由 `authentication.0011_connection_token_ticket` 改为指向 `Ticket`，原 ID 不变。部署时后端与 Lina 需同时切换；旧的四类专用工单地址不再提供。

## 部署和验证

需要部署后端及 Lina，并执行 `tickets.0013_ticket_plugins`、`tickets.0014_workflow_cc_nodes`、`tickets.0015_ticket_origin`、`authentication.0011_connection_token_ticket`、`tickets.0016_merge_ticket_models`、`tickets.0017_single_asset_beneficiary` 和 `tickets.0018_ticket_secret_access` 迁移。`0017` 增加代申请权限并为历史资产授权工单补建授权用户关联；`0018` 增加密码查看授权表。迁移不改历史申请人、不重放历史授权。代申请需给发起人授予新权限，且发布经过组织管理员的流程版本。为新增类型创建并发布流程后，用户才能提交该类申请。中文文案加入中简/中繁语言源文件，按既有部署流程编译翻译。

在 `tickets.tests.settings` 隔离环境运行 `tickets.tests.test_plugins` 及既有工作流测试。历史迁移和并发测试使用文档 `ticket-workflow-refactor.md` 中的独立 PostgreSQL 测试库，避免 SQLite 的 schema editor 限制。

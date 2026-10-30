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
| `file_transfer` 文件上传下载 | 用户申请 | Linux SSH/SFTP；上传指定文件到指定目录，下载指定路径；审批通过后申请人手动执行 |
| `download_replay` 录屏下载 | 用户申请 | 审批后允许申请人在有效期内下载指定会话录屏 |
| `change_secret` 账号改密 | 用户申请 | 新工单通过后异步执行 PAM 随机密码改密，详情展示执行与核验结果 |

`view_secret` 已接入授权 handler 和插件动作入口；审批时不读取或保存密码。`file_transfer` 提供审批后手动执行的文件传输；`download_replay` 已接入对应授权；`change_secret` 创建异步改密任务，审批结果与任务执行结果分开展示。不能把 approved 直接解释为操作已经执行。

`applicant` 始终是实际提交者。资产授权插件使用 `request_data.apply_users` 保存单个授权用户 UUID 的列表，省略时默认申请人自己。代他人申请需要本组织的 `tickets.apply_asset_for_others` 权限，并且选用的流程每条路径都必须经过组织管理员审批。申请人和授权用户都不能审批该工单，包括转交和加签。受理前后均检查组织和用户有效性；`@USER` 的上下文和授权校验针对授权用户。旧工单没有该参数时仍给原申请人授权。历史多人授权工单保持原有快照和授权，不重新执行。

授权用户通过 `TicketBeneficiary` 关联查询自己的工单和流程实例，并在工单结束时收到结果通知。原 `applicant` 保留发起人、撤回人和审计身份；`applicant_manager` 与 `org_admin` 均解析为工单所在组织的管理员，均可用于代申请所需的组织管理员审批。

工单公共字段 `origin` 记录创建入口，与类型、执行模式和审批结果分开：用户经申请 API 提交为 `manual`，ACL 等业务入口为 `system`。账号页操作入口提交 `view_secret` 时也标记为 `system`。插件元数据的 `creation_modes` 声明支持 `manual` 和/或 `operation`；同一个类型可以同时支持两种来源，不能按类型推断来源。历史登录、资产连接和命令复核工单在迁移中标记为 `system`。我发起的列表按来源切换，默认只显示进行中，已完结和全部可通过状态筛选查看。

工单和运行中的流程实例以 `org_id` 记录业务归属；普通用户申请必须选择一个具体组织，资源、授权用户、审批人和权限检查都以该组织为准。流程定义可以放在根组织供各组织复用，但实例仍属于提交工单的组织。系统登录复核插件的 `allow_global` 是显式例外。个人的“我发起的／待我审批／为我申请”列表汇总本人在各组织的相关工单，详情中的组织名称和审批操作所带的 `oid` 用于识别、切换工单归属；审计工单列表则按当前组织筛选，根组织可查看全部。

## 资产工单重新申请与续期

资产授权工单的原申请人可以对拒绝、关闭、审批过期或异常的工单重新申请；已通过工单的原申请人及授权用户可以申请续期。授权用户只为自己续期，原申请人代他人申请仍须满足当前代申请权限和流程要求。待审批工单不提供重复申请入口。

操作入口位于工单列表每行的图标操作按钮，详情不单独放置按钮；单个操作直接展示，不放进下拉菜单。列表的 `reapply_action` 由服务端按当前用户关系、组织成员资格和状态返回 `reapply`、`renew` 或空值；不可用时保留图标并禁用，进入表单和提交时仍独立检查权限。

`GET tickets/{id}/actions/reapply_asset/` 返回可编辑的申请预填值和失效提示。资产来自审批时的具体资源快照，不重新展开旧节点；旧工单没有可靠快照时，只带回具体资产，并提示重新选择节点。已删除、停用或不在当前申请范围内的资产、失效账号不会带回。重新申请从当前时间开始，续期从当前时间与原授权到期时间中的较晚者开始，时长采用当前默认授权时长。用户仍需确认有效期并提交。

提交仍走 `POST tickets/open/`，额外传入 `source_ticket_id`。后端重新检查来源关系、组织成员、当前资源范围、账号、有效期及所选流程；按该流程最新发布版本生成新工单，原工单与原授权不修改。来源记录存于 `meta.source_ticket`，新工单详情只向有权查看来源的用户提供链接。切换组织会清空表单中的资源和授权用户，并作为新的重新申请处理。

工单指定的到期提醒与按天汇总的资产到期提醒均为有资格续期的用户提供申请链接。链接只打开表单，不自动提交或授权；普通授权规则没有来源工单时不提供续期链接。本阶段仅支持资产授权，其他工单类型、附件复用及执行重试不在此范围内。

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

这样即可使用统一接口和前端申请页，不必新增 TicketType 枚举成员、模型、迁移、ViewSet 或 URL。点击“申请工单”会从 `/ticket-types/` 加载可自助申请的类型，在抽屉中选择后打开对应表单；新增类型自动出现在抽屉中。表单支持文本/UUID、文本列表、单选、多选、布尔、整数、日期时间及资产/账号/会话选择。DictField、嵌套 Serializer 和非文本列表等不支持的字段会在启动时明确报错；复杂表单声明 `custom_form = True`，并在 Lina 注册专用组件。当前资产授权保留专用表单，数据统一保存在 `Ticket.request_data`。

树形多选字段可复用 `TreeChoicesField`（例如资产授权的 `ActionChoicesField`）。字段描述保留 `multiple_choice` 类型和 `choices`，同时返回 `tree`；通用申请页与审批资源编辑据此复用 `BasicTree`，保留分组、勾选联动和协议提示。提交值仍为具体权限项列表，不包含分组节点。

插件发现期间不要导入模型或 Serializer，使用字符串路径及方法内导入，避免 Django 初始化循环。注册表检测重复/非法标识、执行模式、申请入口和动作映射；模型加载完成后统一检查 Serializer、表单字段、动作处理器及其权限/限流类，配置错误阻止启动。移除插件前应处理历史工单和在途实例，不能直接删除仍被引用的类型。

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
- `on_approved(instance, ticket)`：可选。默认无操作；自动执行的插件显式声明 `execution_mode = 'automatic'`，成功后返回事件数据，框架才记录 `action.executed`。异步任务提交返回 `pending: true`，改为记录 `action.submitted`，不宣称远程执行成功。读取 `instance.context`，不重新读取可变的申请参数作为授权依据。
- `get_result(ticket, user)`：返回详情中的实时 `result`，至少包含 `state` 和 `actions`；按类型追加非敏感的资源说明、有效期等。每次读取时检查当前查看者、授权、对象和时效，绝不返回密码或持久化此结果。列表返回 `result: null`，不执行该查询。
- `actions`：动作名到 `TicketAction` 子类的导入路径映射。新增动作不需要新增 ViewSet 或 URL；处理器声明 `method`（GET/POST）、`permission_classes`、`throttle_classes`，实现 `execute(ticket, request)`。
- `get_execution_mode(ticket)`：详情展示和最终审批执行共同使用的判断入口。默认返回当前插件的 `execution_mode`；需要历史策略时，在插件内根据服务端快照判断。`approval_only` 不调用 `on_approved`，未知模式阻止执行。
- `custom_form`：复杂申请参数使用专用前端表单；仍必须配置服务端 Serializer 验证参数。
- `options(request, org_id)`：按 `field` 查询参数返回指定资源字段的选项；所有范围与依赖都须在服务端重新验证。
- `get_result_resources(instance, event, user)`：可选。展示业务动作产生的对象，默认读取事件中的 `resources` 快照并返回纯文本；插件可增加本地化 `label` 和当前用户有权访问的站内 `url`。统一活动列表直接渲染，无需按工单类型增加前端分支。
- `execution_mode = 'external'`：由现有业务入口消费审批结果，例如登录和命令复核。

### 实时结果、动作和前端扩展

审批副作用、实时状态和用户动作分开：

1. `on_approved` 创建授权或业务任务，分别记录 `action.executed` 或 `action.submitted` 历史事件。
2. `get_result` 描述当前用户此刻能做什么；异步任务返回 `processing: true` 时，详情继续轮询直到结束。例如查看密码工单：
   ```json
   {"state": "available", "expires_at": "...", "actions": [
     {"type": "view_secret", "account_id": "...", "name": "root", "expires_at": "..."}
   ]}
   ```
3. 用户点击后调用 `tickets/{id}/actions/{action}/`。公共入口核对工单可见性、当前组织和有效成员身份，并在工单组织内执行动作的 DRF 权限及对象权限；标准限流与动作限流叠加。处理器重新核验业务授权，返回 JSON 或文件响应，统一禁止缓存。

`account_id` 等客户端字段只是选择器，不是授权依据：必须属于该工单冻结的对象或已生成的授权。密码读取复用 `accounts.ticket_secret.reveal_ticket_secret`，录像复用 `SessionViewSet.build_replay_download_response`；不能直接调用另一个 APIView 的方法来绕过它的权限、MFA、限流或审计。复杂任务使用已有业务任务机制，不在请求中阻塞等待。

Lina 的 `src/views/tickets/plugins/registry.js` 是唯一的类型扩展配置入口，按需配置：

- `form` / `createRoute`：专用申请表单或已有申请路由；普通类型直接用元数据表单。
- `requestComponent` / `resultComponent`：申请信息及实时结果组件，接收完整 `object`，读取 `object.result`。复用现有组件时只增加注册配置；全新交互需要新增组件。
- `fields`、`requestLabels`、`requestChoices`、`dateFields`：本地化字段说明及展示。
- `detailRoute`：保留 dev 既有详情入口；新类型默认通用详情。

后端只返回数据，不能指定任意 Vue 文件路径或动态执行脚本。注册表中的组件随前端发布；后端声明了专用表单但前端未注册时，显示明确提示，不允许提交缺失参数的通用表单。新类型一般只需后端类型目录；有特殊交互时再增加前端组件及这一处注册，不再修改公共详情序列化器或公共详情页的类型分支。

`get_result_resources` 只负责历史事件中的业务对象展示；历史“执行成功”不代表当前授权仍有效，不能用它替代 `get_result`。

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

- `GET ticket-types/`：类型名称、申请方式、执行模式、`custom_form` 和参数描述。
- `GET tickets/{id}/`：在已有详情响应中返回 `result`，无需额外的 result 轮询接口。
- `POST tickets/{id}/actions/view_secret/`：传 `account_id`，在 MFA 和实时授权检查后读取当前密码。
- `GET tickets/{id}/actions/download_replay/`：限流后下载已批准会话的录屏，打包完成、发送文件前再次检查授权。
- `GET ticket-types/{type}/options/?org_id=...&field=accounts&asset=...`：账号字段选项；账号字段通过 `style={\"resource\": \"account\", \"depends_on\": \"asset\"}` 声明依赖。多个账号/资产字段分别加载、分别清空；自定义字段名或依赖由插件的 `options()` 实现。
- `POST tickets/open/`：统一申请入口。
- `GET ticket-types/apply_asset/options/?org_id=...&search=...`：本组织有效授权用户选项。
- `GET workflows/options/?type=apply_asset&org_id=...&beneficiary=...`：代申请时只返回每条路径均有组织管理员审批的流程。
- ACL 入口继续可用；资产申请与三类复核工单的专用 API 已并入 `tickets/open/` 和 `tickets/{id}/`。资产富表单从 `OPTIONS tickets/?type=apply_asset` 获取字段描述。
- 工单读取结果新增 `request_data`、`request_items`、`execution_mode` 和只读 `origin`，列表可用 `origin=manual|system`、`status=open|closed` 筛选；审批任务、撤回、评论等 API 不变。
- `GET /api/v1/accounts/accounts/{account_id}/request-secret-ticket/`：账号页获取本组织可选的已发布密码查看流程。
- `POST /api/v1/accounts/accounts/{account_id}/request-secret-ticket/`：传 `workflow_id`、`duration` 和可选 `comment`，创建 `origin=system` 的 `view_secret` 工单并返回工单 ID。服务端从账号对象确定资产、用户名和组织，不接受客户端指定授权对象。
- `POST /api/v1/accounts/accounts/{account_id}/reveal-by-ticket/`：账号业务入口保留的薄适配器，和插件动作复用同一取密服务及 MFA；工单页面统一使用 actions 接口。

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

资产授权在 `request_data` 内填写原 `apply_assets`、`apply_accounts`、`apply_actions`、日期等字段以及可选 `apply_users`（只能有一个 UUID）。申请人不能通过传入别人的 applicant 来代申请，应填写 apply_users。提交上下文记录插件类型，不再保存不参与执行的 `execution_mode` 副本。展示和执行都以 `get_execution_mode(ticket)` 为准，特殊历史策略由各插件处理。文件传输通过服务端快照版本标记保持历史工单仅审批，不因升级而补发授权；密码查看和录屏下载按对应插件的现行授权校验处理。

`view_secret` 审批完成后，handler 只创建数据库中的 `TicketSecretAccess` 授权，绑定工单、账号 UUID、申请人、组织与过期时间。详情的 `result.actions` 只向符合条件的申请人展示查看按钮；点击时插件动作及账号取密服务 重新检查工单状态、授权时效、组织成员、账号有效性及全局禁止查看密码配置。若启用了查看密码 MFA 设置，动作入口仍要求 MFA。密码从当前账号读取，不写入工单、事件、缓存或访问链接；审批后轮换密码时读到的是新密码。授权记录是唯一的权威状态，未来可加短时缓存加速，但撤销、过期和全局禁止策略必须保持实时有效。

`tickets.0010_ticket_workflow_refactor` 将四种旧多表继承工单的业务字段和关联 UUID 搬入通用 `request_data`，再删除子表。连接令牌的 `from_ticket` 先由 `authentication.0012_connection_token_ticket` 改为指向 `Ticket`，原 ID 不变。部署时后端与 Lina 需同时切换；旧的四类专用工单地址不再提供。

## 部署和验证

本轮插件接口整理不新增模型或迁移。重构分支的 `available_actions`、`secret_access_status`、`replay_access_status`、`file_transfer_status` 合并为 `result`，原录屏工单下载路径替换为 actions 路径；Core 和 Lina 必须同步部署，不保留这部分试验接口的双写/双读。dev 的四类旧工单、UUID、审批策略、授权记录和迁移导入继续保留，读详情不会补跑业务效果。

插件接入回归包括：新类型无需修改枚举/模型/路由即可申请、审批、读取结果并执行动作；Boolean/MultipleChoice 参数往返；未知动作和错误 HTTP 方法拒绝；查看者与执行者权限隔离；MFA、限流、过期、跨组织及资源变更拒绝；列表不查询实时授权。Lina 覆盖多个账号依赖字段隔离、组织切换丢弃旧响应、结果刷新、过期和专用表单缺失提示。

需要同时部署后端及 Lina，以 dev 迁移为基线，执行 `authentication.0012_connection_token_ticket`、`tickets.0010_ticket_workflow_refactor`、`assets.0033_workflow_foundation` 和 `acls.0008_ticket_workflow_integration`。assets 0033 接在 dev 的 OceanBase 0032 之后。工单重构的模型、业务字段搬迁、代申请权限、历史受益人关联与密码授权表统一在 tickets 0010 中完成。迁移不改历史申请人、不重放历史授权。代申请需给发起人授予新权限，且发布经过组织管理员的流程版本。升级执行 migrate 后自动导入旧流程，并为缺少的可见类型补齐已发布、已启用的默认流程，用户无需等待管理员手工创建；默认沿用系统管理员一级或签，已有流程及其停用状态不覆盖。中文文案加入中简/中繁语言源文件，按既有部署流程编译翻译。

在 `tickets.tests.settings` 隔离环境运行 `tickets.tests.test_plugins` 及既有工作流测试。历史迁移和并发测试使用文档 `ticket-workflow-refactor.md` 中的独立 PostgreSQL 测试库，避免 SQLite 的 schema editor 限制。


## 资源说明与审批人调整

首批支持 `apply_asset` 和 `view_secret`。插件声明 `resource_serializer` 和 `resources_pending(data)`；专用 serializer 只列出允许调整的资源、动作及有效期字段，不能修改申请人、受益人、组织、流程或原始用途说明。普通类型无需实现这些扩展。申请表单仍使用原有资产、节点和账号控件；资产授权保留代申请、动态账号、动作及到期提醒。

- `GET ticket-types/{type}/options/?org_id=...&field=availability` 返回 `description_allowed`；查看密码可传 `asset`，资产授权可传逗号分隔的 `apply_assets`、`apply_nodes`。服务端按 `TICKET_APPLY_ASSET_SCOPE` 独立检查空资源条件，不能把网络失败、越权、搜索无匹配当作空列表。
- 无可选资源时传 `resource_description`，以及已有资源和原表单的其他参数。资源未补齐时不会生成授权。若流程在到达审批节点前必须根据缺失的资源解析负责人或条件，提交会报配置错误；需要选择能先解析出审批人的流程，不会猜测资源或跳过条件。
- 工作流详情新增 `resource_adjustment`，包含 `pending`、`revision`、`can_adjust`；当前有权限的审批人还会收到调整字段及当前值。被指定为审批人不会自动获得资源查询权限，须具有工单组织的 `assets.view_asset` 和 `accounts.view_account`；使用节点还需 `assets.view_node`。
- `GET approval-tasks/{id}/resource-options/?resource=asset|account|node` 查询本组织资源，账号查询通过 `assets` 传资产 UUID。
- `POST approval-tasks/{id}/adjust-resources/` 接受 `resources`、必填 `reason` 和 `expected_revision`。独立保存，不审批；失败全部回滚，重复旧版本请求返回 409。原说明一直保留，`resources.adjusted` 事件记录修改前后内容和调整原因，不包含密码。
- `POST approval-tasks/{id}/approve/` 传 `expected_revision`。修改后需要重新核对详情，旧页面、旧邮件及不携带新版号的批量审批不能批准修改后的范围。已有投票、已走过条件分支，或当前资产负责人审批节点的资产范围／负责人发生变化时，重新执行同一个发布版本的流程，旧任务保留在历史中并作废未处理待办。新节点按原配置重新计时、解析负责人；新资源缺少有效负责人时整次调整回滚。其他没有投票或条件分支的首次补齐保留当前节点、转交／加签和截止时间。

资源调整的模型变更已合入 `tickets.0010_ticket_workflow_refactor`，不创建“一个节点只能运行一次”的约束，使重新审批保留旧节点与任务记录；不清理历史数据、不重放授权。已执行旧开发版 tickets 0010／0011 或 assets 0032 工单迁移的预览环境，应按升级说明从 dev 数据库备份恢复后验证，不能直接 fake 新迁移。

手工验收：

1. 设置可申请范围为 `permed_valid`，用尚无授权的普通用户分别打开资产授权、查看密码原表单；应出现用途说明，填写后可提交。切换组织会清理旧资源，接口失败时应重试，不出现可绕过校验的说明模式。
2. 用无资产／账号查询权限的审批人打开，不能枚举或调整资源，资源不完整时不能同意；可按原流程配置拒绝或转交。
3. 用有本组织查询权限的当前审批人，在原“申请信息”区域点击“编辑”，原位置切换为资源表单，补齐资产、账号、动作／有效期及原因；点击“保存修改”后恢复详情显示，工单仍待审批，尚无资产授权或密码查看授权。审批进度区域只保留原审批操作。
4. 核对详情资源和原说明，再单独同意。申请人获得对应授权或密码查看按钮，原有时效、MFA、组织边界校验继续生效。
5. 在多人或多级流程已有一票通过后调整范围；应从原流程重新审批，旧票不计数，旧页面提交应报冲突。活动记录可查看修改原因及前后内容。
6. 验证正常资源可选的申请、节点／动态账号、代申请、到期提醒、拒绝和撤回，以及其他工单类型仍按原流程工作。

自动回归见 `tickets.tests.test_resource_adjustment` 和 Lina `ticketResourceAdjustment.test.mjs`。

## 账号改密执行

新申请在服务端快照中保存 `change_secret_version=1`。没有该标记的历史工单保持仅审批，即使尚未审批结束也不会因升级自动改密。

仅接受本组织可申请资产上、有效且允许改密的密码账号。资产须有效，平台须启用 Ansible 和改密方法。申请、最终审批及异步执行前均检查许可证、申请人资格、资产范围及账号状态；按冻结的账号 UUID、用户名和密码类型核对，删除重建、改名、停用或移出组织后拒绝执行。沿用 PAM 安全模式对特权账号的限制。暂不支持 SSH 密钥轮换或申请人提交指定密码。

最终审批在同一事务内，以工单 UUID 创建唯一的 `AutomationExecution`，只在提交后投递到 `ansible` 队列；事务回滚不会投递。复用 PAM 的随机密码规则、改密管理器、账号锁及改后验证，不将新旧密码写入工单参数、上下文、事件或结果。密码只由现有 PAM 凭据与执行记录机制管理。

投递失败或进程退出留下的待执行记录由每分钟运行的 `dispatch_ticket_change_secrets` 补发，同一记录五分钟内最多投递一次。工作进程先锁定并领取未开始的执行；重复投递不能再次改密。已经开始的任务不会自动重跑，沿用 PAM 中断恢复、核验和管理员处理流程，避免密码状态不确定时再次轮换。

详情通过现有工单接口返回排队、执行中、成功、失败和待核验状态及账号数量，不返回底层日志或密码。只有全部目标账号都有成功记录才显示成功；未执行的账号不能被误报为成功。任务启动后，有本组织改密执行查看权限的用户可通过 `log_task_id` 直接打开实际 Celery 任务的执行日志，日志页继续执行现有权限校验。其他工单查看者只看到非敏感的执行摘要。

部署需要同时更新 Core、Celery worker/beat 和 Lina，无新增数据库迁移。自动回归见 `tickets.tests.test_change_secret`、Lina `ticketChangeSecretResult.test.mjs` 和 `workflowReassign.test.mjs`。真实资产验收需检查：审批前不改密；最终通过后每个账号仅执行一次；成功密码可登录；验证失败显示待核验；拒绝、撤回及历史工单不执行；账号状态变化或许可证失效阻止任务启动。

## 历史文件上传下载授权（v1）

以下行为仅适用于已保存服务端 `file_transfer_version=1` 快照的工单；新提交使用下方 v2 流程。升级前已创建的工单，无论是否结束，都保持仅审批，不补发权限。

申请人必须是组织有效成员，且对所选资产账号已有有效连接权限。申请及最终审批均检查访问范围；冻结具体账号 ID、用户名和已有 SSH/SFTP/RDP 协议。账号删除重建、停用、跨组织移动或基础权限失效后，工单不能单独提供访问权限。新增基础授权也不会扩大工单冻结的协议范围。权限排除规则和连接 ACL 继续生效。

审批通过创建工单 ID 对应的 `AssetPermission`，只包含上传或下载方向，不增加连接、删除、剪贴板权限。该记录不参与基础权限合并，仅在文件管理和连接令牌的账号解析中追加动作；不额外授权作业中心的批量文件分发任务。重复处理不续期。有效期从最终审批通过开始，默认 3600 秒，可选 60–86400 秒。

路径仅作为申请用途说明，不限制实际传输路径。授权到期后，新建连接和令牌兑换不再获得这张工单追加的动作；其他独立授权不受影响。已有会话沿用执行端原策略，可能在到期后继续使用，不承诺即时中断。

文件传输工单详情的 `result.state` 返回 `approval_only`、`pending`、`available`、`expired` 或 `unavailable`，以及方向、账号、协议、生效时间和到期时间。审批通过后，申请人须通过现有文件管理入口新建连接使用授权。该状态只表示此工单的授权，不能代替连接时的实时权限检查。

### 手工验收

1. 给测试申请人配置一个资产账号的 SSH/SFTP 基础连接权限，不授予上传、下载、删除；准备对应文件传输审批流程。
2. 新建文件上传工单，选择该资产账号，填写路径说明，将有效期设为 60 秒。待审批时新建文件管理连接，确认仍无上传权限。
3. 审批通过后检查工单显示已授权、方向和截止时间；以申请人重新建立文件管理连接，确认可以上传，不能下载或删除。另建下载工单验证反向隔离。
4. 等待有效期结束后重新建立连接，确认此工单提供的方向不再可用；已有连接不作为到期验收依据。
5. 在授权有效期内撤销基础账号访问权限，重新连接应失败；其他账号、其他用户及未获批协议不得获得该工单的权限。
6. 检查拒绝、撤回和历史工单均不生成授权；已有独立上传／下载授权不被工单到期影响。

自动回归：后端 `tickets.tests.test_file_transfer`；前端 `yarn test` 包含状态到期、组织切换、审批刷新和表单说明测试。还需结合实际部署的 Koko/RDP 执行端完成上述真实文件验收。


## 指定文件传输（v2，Linux SSH/SFTP）

申请人选择已有连接权限的一台 Linux 资产、一个密码或 SSH 私钥账号，再选择上传或下载。资产 SSH 服务必须提供 SFTP 子系统，支持现有资产网关；本期不支持 RDP、Windows、SSH 证书、提权、目录递归或通配符。

- 上传：提交时上传最多 20 个不同名文件，填写已存在的目标绝对目录。审批人可下载核对实际文件。服务端冻结文件 ID、大小、SHA-256、账号、协议、地址、端口和目标目录；最终通过后由申请人在有效期内点击“执行上传”。上传使用同目录临时文件和不覆盖的 SFTP rename，不创建目录或覆盖现有文件，目标文件权限为 0600。
- 下载：提交最多 20 个具体文件绝对路径。最终通过后申请人点击“获取文件”，成功文件暂存至私有共享目录，申请人随后逐个下载到本机。审批人和抄送人不能领取远端下载结果。下载的是执行时的文件内容，不是申请时的远端快照；传输期间检测到大小或修改时间变化会拒绝提供结果。
- 有效期从最终审批通过开始，默认一小时，可选 60–86400 秒。到期后禁止开始执行和领取文件，正在传输的任务也会检查到期；网络操作单次超时 30 秒，任务最长 15 分钟。点击执行不接受客户端另传路径或文件，重复点击/重复 Celery 投递只领取一次。失败必须核对后重新申请，不自动重试已开始的传输。
- 每个文件分别返回状态、路径、大小和失败原因；部分失败不会抹掉成功记录。上传完成应答丢失或 worker 中断时标记待核验，不声称回滚远端文件。中断可能留下 `.jms-transfer-<文件 UUID>` 临时文件，需要管理员核对后清理。工单时间线记录提交执行、开始、结果及领取下载文件，已有 FTP 审计记录实际传输结果。

v2 不创建通用上传/下载 AssetPermission，也不放开 Koko 文件管理入口。提交、最终审批、执行入口和 worker 均检查现有基础访问权限，执行还检查申请人的连接 ACL 和动作排除规则；传输中每五秒再次检查权限。跨组织访问、其他用户执行、换账号、换协议/端口/地址和修改已批路径均被拒绝；用户已有独立授权不受影响。历史 v1 和无版本的仅审批工单继续原有行为，读取详情不会触发执行。

路径必须落在平台 SFTP 根目录内（采用平台 sftp_home 配置，未配置 SFTP 协议时默认 `/tmp`），逐级拒绝软链接，仅允许普通文件及现有目录。标准 SFTP 的路径检查与打开操作无法在远端原子绑定：使用可信、稳定的目标目录；需要防御远端其他用户同时替换目录时，须额外使用远端 chroot/账号目录权限隔离。此实现不是远端文件系统沙箱。主机密钥策略沿用资产自动化当前 SSH 行为。

文件内容放在 `SHARE_DIR/ticket_transfers/<org>/<UUID>`，不进入公开 media 路径，目录/文件权限为 0700/0600。单文件遵循 `FILE_UPLOAD_SIZE_LIMIT_MB`，最大 1 GiB；每用户每组织最多保留 100 个文件。未提交文件保留 24 小时，待审批文件最多 30 天，审批通过后按工单有效期到期；拒绝/关闭等结束状态或到期后由定时任务删除内容、保留元数据和结果。下载结果同样计入配额，领取不会删除文件，有效期内可以再次领取。

### 部署与验收

1. 应用 `tickets.0010_ticket_workflow_refactor`（已包含文件元数据和单次执行记录两张表，不再单独新增文件传输迁移），同步部署 Core 与 Lina。API 与 worker 必须共享同一个私有 `SHARE_DIR`，不能由 Web 服务器公开。
2. 更新并重启 Celery worker 与 beat，确保 worker 消费 `ansible` 队列。`execute_ticket_file_transfer` 执行传输；`maintain_ticket_file_transfers` 每五分钟补发排队任务、标记中断，同一排队记录五分钟内最多补发一次。`cleanup_ticket_transfer_files` 每小时清理过期或工单已终止的文件，每批 100 个，在同一任务中连续处理所有符合条件的批次，不逐文件投递任务。删除失败的文件保留元数据、记录错误并留待下轮重试，不阻断其他文件清理；执行中的文件跳过，删除前再次检查清理条件。文件到期后立即禁止访问，物理删除通常在下一轮小时清理时完成（队列延迟、执行中或删除失败时可能更晚）。
3. 使用隔离测试资产验收：申请上传→审批人核对附件→批准→申请人执行→核对远端文件及权限；再申请具体路径下载并核对内容。检查审批前、其他用户、不同组织、过期/权限撤销、同名目标、软链接、目录不存在、连接失败和部分文件失败。

自动回归：后端 `tickets.tests.test_file_transfer_execution` 包含临时 SSH/SFTP 服务器协议读写、单次执行、审批快照、权限、附件访问及清理；`tickets.tests.test_file_transfer` 继续验证 v1。Lina 的 `ticketPluginForm.test.mjs`、`ticketFileTransferResult.test.mjs`、`ticketFileTransferAccess.test.mjs` 覆盖新旧表单、组织切换、按钮重复点击和文件领取权限。真实资产凭据、网关、部署目录挂载和断网场景仍需部署验收。

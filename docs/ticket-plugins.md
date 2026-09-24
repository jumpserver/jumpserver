# PAM 工单类型插件

审批引擎继续负责流程、任务、状态和时间线。每个业务类型在 `apps/tickets/plugins/<type>/` 中提供 `plugin.py`，启动时自动发现 `Plugin` 类。类型标识必须唯一且保持稳定；这是一套随应用代码发布的扩展方式，不支持上传代码或运行时安装。

## 本次范围

| 类型 | 申请方式 | 审批完成后的行为 |
| --- | --- | --- |
| `apply_asset` 资产授权 | 用户申请 | 按冻结的资源、账号、动作、有效期和授权用户创建权限 |
| `login_confirm` 系统登录复核 | ACL 触发 | 原登录入口读取审批结果 |
| `login_asset_confirm` 资产登录复核 | ACL 触发 | 激活原连接令牌 |
| `command_confirm` 命令复核 | ACL 触发 | 原命令入口读取审批结果 |
| `view_secret` 查看账号密码 | 用户申请 | 仅审批与留痕 |
| `file_transfer` 文件上传下载 | 用户申请 | 仅审批与留痕 |
| `download_replay` 录屏下载 | 用户申请 | 仅审批与留痕 |
| `change_secret` 账号改密 | 用户申请 | 仅审批与留痕 |

新增四类没有自动取密、下载、传输或改密，也未改变现有业务 API 的权限。申请页和详情页明确提示不会自动执行。后续按业务逐类接入 handler 或消费审批结果，不能把 approved 直接解释为操作已经执行。

`applicant` 始终是实际提交者。授权用户不属于工单公共字段：资产授权插件使用 `request_data.apply_users` 保存 UUID 列表，支持 1–100 人，默认申请人自己。所有人共用一套申请范围并整体审批；受理前后均检查组织和用户有效性，任一用户失效则不创建部分授权。`@USER` 的上下文和授权校验针对授权用户。旧工单没有该参数时仍给原申请人授权。

工单公共字段 `origin` 记录创建入口，与类型、执行模式和审批结果分开：用户经申请 API 提交为 `manual`，ACL 等业务入口调用 `open_by_system()` 为 `system`。新增自动触发入口也应调用该方法，不能按类型推断来源；一个类型将来可以同时有两种来源。历史登录、资产连接和命令复核工单在迁移中标记为 `system`。我发起的列表按来源切换，默认只显示进行中，已完结和全部可通过状态筛选查看。

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
- `request_serializer`：校验类型参数，包含资源范围及申请资格检查。继承 `RequestSerializer` 可拒绝未声明字段，密码和私钥等敏感值不进入申请数据。
- `build_context(ticket)`：构建审批条件需要的服务端快照。默认把参数置于 `context.request`，公共代码固定申请人和请求类型。资产/账号条件可复用 `snapshot_assets` 及 `account_context`。
- `on_approved(instance, ticket)`：可选。默认无操作；自动执行的插件显式声明 `execution_mode = 'automatic'`，成功后返回事件数据，框架才记录 `action.executed`。读取 `instance.context`，不重新读取可变的申请参数作为授权依据。
- `execution_mode = 'external'`：由现有业务入口消费审批结果，例如登录和命令复核。

handler 在实例锁和审批数据库事务内执行。数据库内的授权可直接完成；远程任务复用业务模块现有的任务提交及幂等机制，不能在这里阻塞等待远程执行，也不能将任务已提交标记为远程执行成功。没有 handler 的类型保持 `approval_only`。

新类型的资源对象归属、操作权限以及后续执行资格由该插件/业务模块负责；组织成员身份和流程类型匹配由公共层校验。录屏申请只允许自己的会话或有会话查看权限的人请求本组织会话；账号类申请遵循现有可申请资产范围配置，只接受该资产上真实存在的账号名。

## API

以下路径均以 `/api/v1/tickets/` 开头。

- `GET ticket-types/`：类型名称、申请方式、执行模式和参数描述。
- `POST tickets/open/`：统一申请入口。
- `GET ticket-types/apply_asset/options/?org_id=...&search=...`：本组织有效授权用户选项。
- ACL 入口继续可用；资产申请与三类复核工单的专用 API 已并入 `tickets/open/` 和 `tickets/{id}/`。资产富表单从 `OPTIONS tickets/?type=apply_asset` 获取字段描述。
- 工单读取结果新增 `request_data`、`request_items`、`execution_mode` 和只读 `origin`，列表可用 `origin=manual|system`、`status=open|closed` 筛选；审批任务、撤回、评论等 API 不变。

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

资产授权在 `request_data` 内填写原 `apply_assets`、`apply_accounts`、`apply_actions`、日期等字段以及可选 `apply_users`。申请人不能通过传入别人的 applicant 来代申请，应填写 apply_users。执行模式随提交上下文冻结，升级 handler 不会让已经提交的 approval_only 工单开始自动执行，也不会把历史审批工单展示成已自动执行。

`tickets.0016_merge_ticket_models` 将四种旧多表继承工单的业务字段和关联 UUID 搬入通用 `request_data`，再删除子表。连接令牌的 `from_ticket` 先由 `authentication.0011_connection_token_ticket` 改为指向 `Ticket`，原 ID 不变。部署时后端与 Lina 需同时切换；旧的四类专用工单地址不再提供。

## 部署和验证

需要部署后端及 Lina，并执行 `tickets.0013_ticket_plugins`、`tickets.0014_workflow_cc_nodes`、`tickets.0015_ticket_origin`、`authentication.0011_connection_token_ticket` 和 `tickets.0016_merge_ticket_models` 迁移。它们依次增加通用参数、迁移流程抄送、补齐工单来源、调整连接令牌外键并搬迁旧业务参数。迁移不改历史申请人、不重放历史授权。为新增类型创建并发布流程后，用户才能提交该类申请。中文文案加入中简/中繁语言源文件，按既有部署流程编译翻译。

在 `tickets.tests.settings` 隔离环境运行 `tickets.tests.test_plugins` 及既有工作流测试。历史迁移和并发测试使用文档 `ticket-workflow-refactor.md` 中的独立 PostgreSQL 测试库，避免 SQLite 的 schema editor 限制。

# 工单审批系统 V1

本次实现设计稿 V1 的完整业务闭环：独立流程定义与版本、流程实例、审批任务、条件分支、任意级审批、或签/会签/N 人通过、撤回、转交、加签、超时、时间线和上下文快照。资产授权、系统登录、资产登录、命令复核均使用新引擎。Lina 提供流程设计器、版本管理、待办/已办、审批操作和执行记录。

设计稿的 V2/V3（通用 Action/CC 节点、并行、Webhook、代理审批、BPMN、风险引擎等）不属于本次 V1。现有业务授权动作和工单级抄送已保留。

## 模型与执行规则

- `Workflow` 管理名称、业务类型、启用状态、工单级抄送及当前发布版本。`WorkflowVersion`、`WorkflowNode`、`WorkflowEdge` 发布后不可修改，只能发布新版本。
- `WorkflowInstance` 固定业务工单、申请人、组织、定义版本和提交上下文。运行中的实例不随流程重新发布而变化。
- `WorkflowNodeInstance` 保存节点状态、实际审批门槛及截止时间；`ApprovalTask` 保存受理人身份快照和每次决定；`WorkflowEvent` 保存完整时间线。
- 所有决策先锁实例，再读取任务最新状态。重复审批返回 409，同一实例的并发投票不能重复完成节点或重复授予权限。
- `any` 一人通过，`all` 全部通过，`quorum` 达到指定人数通过。任何拒绝终止流程；加签是原门槛之外的必签任务；转交保留原任务是否为加签的属性。转交和加签不延长截止时间。
- 审批人支持用户、用户组、角色、组织管理员、申请人直属负责人和资产负责人。默认排除申请人。组/角色成员在节点进入时解析；直属负责人和资产负责人来自提交快照。所有受理人仍必须是有效组织成员。
- 新增 `User.manager` 和 `Asset.owner`，删除被引用用户时置空。用户不能通过自助修改自己的直属负责人来改变审批路径。
- 普通业务实例必须属于具体组织；系统登录复核是明确允许的全局组织特例。
- 定时任务 `tickets.tasks.expire_workflow_approvals` 每分钟处理最多 500 个到期实例。人工操作也检查截止时间，定时任务延迟不会使过期任务被通过。

## 业务适配

`workflow/engine.py` 只负责审批状态推进，通过同步领域信号通知 `workflow/business.py`。业务效果和实例终态位于同一数据库事务内；通知只在事务提交后发送。

资产申请提交时必须填写资源、账号、动作和有效期。服务器展开节点为具体资产，记录资产标签、平台、负责人及账号元信息，不读取或保存密码、私钥等凭据。`@ALL` 在提交时展开为当时存在的账号用户名；手工输入等无法预知的用户名在快照中为 null，涉及具体用户名的条件因此失败关闭，而不会当作低风险账号绕过审批。

最终通过后，只按快照创建 `AssetPermission`，使用工单 ID 保证幂等，不再把原始资产节点加入授权规则。审批期间新增到节点的资产、后续出现的新账号名不会被这张工单额外授权。原有虚拟账号选择器（例如 `@INPUT`、`@USER`）仍保留其明确的授权语义。申请人失效、请求资产已删除/移出组织、请求有效期已结束时，流程进入异常且不授予权限。普通存储错误会回滚决定，允许重试。

资产登录最终通过后激活对应连接令牌；系统登录和命令复核通过统一 Ticket 状态向原有业务消费者返回结果。ACL 可选择同类型已发布流程；未选择时，原审核人配置自动生成使用同一新引擎的单节点版本。自动生成的定义和历史工单专用定义不出现在流程配置列表中。

工单邮件操作链接固定到具体 ApprovalTask，不能使用旧节点邮件批准同一用户之后收到的节点。抄送者只能阅读，不能处理审批任务。

## 上下文与条件

上下文只由服务器业务适配器生成，没有接受客户端任意 context 的启动接口。主要字段：

- `applicant.id/name/username/manager_id`
- `assets[].id/name/address/labels/platform/owner/owner_ids`
- `accounts[].username`，实际账号还包含 `id/asset_id/secret_type`，虚拟账号包含 `selector`
- `actions`：动作名称数组；`duration`：有效期秒数
- `nodes[]`：提交选择的节点标识，仅用于审计
- `request.type/title`，以及资产授权有效期/权限数据、命令及会话 ID、登录 IP 等对应业务数据

支持 `eq/ne/gt/gte/lt/lte/in/not_in/contains/exists`、`and/or/not`，不执行任意代码。`asset.*`/`account.*` 是复数集合路径的别名。集合默认任一匹配，`ne/not_in` 默认全部匹配，可显式配置 `quantifier: any/all`。同名多值标签是数组，使用 `contains`。不存在或类型不匹配的字段会导致异常；`exists` 用于显式判断字段是否存在。风险字段虽然允许出现在 DSL 中，但 V1 业务适配器没有风险评分来源，不会自行编造评分。

## API

以下路径均以 `/api/v1/tickets/` 开头，组织沿用 `X-JMS-ORG` / `oid`。

| 路径 | 用途 |
| --- | --- |
| `workflows/`、`workflows/{id}/` | 创建、查看、修改元信息，需 `tickets.*_workflow` 权限 |
| `workflows/options/?type=apply_asset&org_id=...` | 申请人可选的已发布、启用流程及抄送人 |
| `workflows/{id}/publish/` | 发布，必须提交 `expected_version` 和 `definition` |
| `workflows/{id}/versions/` | 分页查看不可变版本及节点图 |
| `apply-asset-tickets/open/` | 使用 `workflow_id` 提交完整资产申请 |
| `workflow-instances/{id}/` | 状态、快照、节点和任务 |
| `workflow-instances/{id}/events/` | 分页时间线 |
| `workflow-instances/{id}/cancel/` | 仅申请人撤回，可带 `comment` |
| `approval-tasks/?state=pending` | 当前用户待办，也可查询已处理状态 |
| `approval-tasks/{id}/approve/`、`reject/` | 固定任务 ID 的同意/拒绝，可带 `comment` |
| `approval-tasks/{id}/transfer/`、`add-approver/` | 目标用户 UUID `target` 和可选 `comment` |
| `approval-tasks/{id}/candidates/` | 当前任务可选择的有效组织成员 |
| `tickets/?processed_by={user_id}` | 已处理的相关工单 |

实例仅申请人、任务参与者、抄送人可读；拥有 `tickets.view_workflowinstance` 的审计员可读当前组织全部实例。任务操作只允许受理人。旧 `flows/` 路由已经移除；按 Ticket ID 进行的 approve/reject/bulk 接口拒绝写入，统一改用任务接口。工单查看、业务状态查询、申请人关闭请求和评论入口保留。

发布例子：

```json
{
  "expected_version": 0,
  "definition": {
    "nodes": [
      {"id": "start", "type": "start"},
      {"id": "prod", "type": "condition", "config": {"field": "asset.labels.env", "operator": "eq", "value": "prod"}},
      {"id": "owner", "type": "approval", "name": "资产负责人", "config": {
        "approvers": {"type": "asset_owner"}, "strategy": "all",
        "allow_transfer": true, "allow_add_approver": true,
        "timeout": 86400, "timeout_action": "expire"
      }},
      {"id": "end", "type": "end"}
    ],
    "edges": [["start", "prod"], ["prod:true", "owner"], ["prod:false", "end"], ["owner", "end"]]
  }
}
```

首次发布后需启用流程。后续发布使用当前版本号作为 `expected_version`，防止覆盖其他编辑者发布的版本。

## Lina

流程配置位于 `/tickets/workflows`。设计器支持可视化插入审批/条件节点、配置真/假分支与汇合、递归组合条件、审批人来源、门槛、超时和操作开关；可查看历史版本并作为新版本发布。后端对完整 DAG 做最终校验。

工单详情展示每个节点的实际受理人、决定、加签属性、截止时间、事件和快照。待办和已办分开，批量处理也使用提交时选中的确切任务 ID。资产与用户表单可维护负责人。新界面提供中英文、繁体中文文案，其他语言使用英文回退文案。

## 上线与迁移

代码没有在开发/生产业务数据库上执行迁移。部署时按以下顺序处理：

1. 备份数据库，暂停产生新工单的入口和审批操作，停止旧版本服务/任务消费者。
2. 部署后端代码，执行 `python apps/manage.py migrate`，包括 assets 0031、users 0008、tickets 0010–0012、acls 0005。
3. 先预览定义迁移，再执行；导入流程默认禁用，逐个检查审批人、组织和抄送配置后启用。
4. 预览并导入历史及未完成工单，检查所有错误和告警；最后同步部署 Lina、重启 Web/Celery/Beat 并恢复入口。

```bash
python apps/manage.py migrate_ticket_workflows
python apps/manage.py migrate_ticket_workflows --apply
python apps/manage.py migrate_ticket_instances
python apps/manage.py migrate_ticket_instances --apply
```

两个命令均支持 `--org-id`；定义命令支持 `--flow-id`，实例命令支持 `--ticket-id`。默认不写入；每个对象单独原子提交，可幂等重跑。旧模型/表保留给迁移及历史核对，不再承接新审批。

定义迁移把旧选择器当时匹配的用户转成固定用户，并记录原规则，便于管理员改成组/角色等动态规则。实例迁移保留原审批人和状态、已完成决定、原时间和删除用户的显示名；历史终态绝不重放授权、令牌激活或通知。未完成工单从原当前步骤继续，后续步骤使用迁移定义。

旧系统没有完整上下文快照，因此无法还原当时的资产标签/负责人/账号等数据。实例迁移明确记录“迁移时采集”的时间、原关系快照和告警。缺少资源或有效审批人的未完成工单转为 error，必须修正后重新申请，不会被静默通过。迁移告警不代表已完成的历史授权被撤销。

## 验证

独立 PostgreSQL 测试库名固定为 `test_jumpserver_workflow_refactor`；测试结束删除。测试设置还隔离 Redis 缓存前缀；通知发送在测试中 mock。安全启动方式（避免应用初始化钩子在测试库建立前访问业务库）：

```bash
DJANGO_SETTINGS_MODULE=tickets.tests.settings WORKFLOW_TEST_POSTGRES=1 .venv/bin/python - <<'PY'
import sys
sys.path.insert(0, 'apps')
sys.argv = ['workflow-tests', 'check']
import django
django.setup()
from django.core.management import call_command
call_command('test', 'tickets.tests.test_workflow', 'tickets.tests.test_workflow_business',
             'tickets.tests.test_workflow_concurrency', 'tickets.tests.test_flow_serializer',
             'tickets.tests.test_deleted_user_history', interactive=False, verbosity=1)
PY
```

覆盖 DSL 校验、8 级审批、分支、版本与快照不可变性、跨组织权限、全部策略、转交/加签/超时、用户删除、四类业务入口、授权快照、令牌激活、历史迁移、邮件任务绑定和真实数据库并发。另运行 Django system check、迁移一致性检查，以及 Lina `yarn lint`、`yarn test`、`yarn build:prod`。

#!/usr/bin/python
from typing import Callable

from django.apps import apps
from django.conf import settings
from django.db.models import F
from django.utils.translation import gettext_lazy as _, gettext, get_language
from treelib import Tree
from treelib.exceptions import NodeIDAbsentError

from common.tree import TreeNode
from .models import Permission, ContentType

# 根节点
root_node_data = {
    'id': '$ROOT$',
    'name': _('All permissions'),
    'title': _('All permissions'),
    'pId': '',
}

# 第二层 view 节点，手动创建的
view_nodes_data = [
    {'id': 'view_console', 'name': _('Console view')},
    {'id': 'view_workbench', 'name': _('Workbench view')},
    {'id': 'view_audit', 'name': _('Audit view')},
    {'id': 'view_setting', 'name': _('System setting')},
    {'id': 'view_other', 'name': _('Other')},
]

# 第三层 app 节点，手动创建
app_nodes_data = [
    {'id': 'users', 'view': 'view_console'},
    {'id': 'assets', 'view': 'view_console'},
    {'id': 'accounts', 'name': _('Accounts'), 'view': 'view_console'},
    {'id': 'perms', 'view': 'view_console'},
    {'id': 'terminal', 'name': _('Session audits'), 'view': 'view_audit'},
    {'id': 'audits', 'view': 'view_audit'},
    {'id': 'rbac', 'view': 'view_console'},
    {'id': 'settings', 'view': 'view_setting'},
    {'id': 'tickets', 'view': 'view_other'},
    {'id': 'labels', 'view': 'view_console'},
    {'id': 'authentication', 'view': 'view_other'},
    {'id': 'ops', 'view': 'view_workbench'},
]

# 额外其他节点，可以在不同的层次，需要指定父节点，可以将一些 model 归类到这个节点下面
extra_nodes_data = [
    {"id": "cloud_import", "name": _("Cloud import"), "pId": "assets"},
    {"id": "backup_account_node", "name": _("Backup account"), "pId": "accounts"},
    {"id": "gather_account_node", "name": _("Gather account"), "pId": "accounts"},
    {"id": "push_account_node", "name": _("Push account"), "pId": "accounts"},
    {"id": "asset_change_plan_node", "name": _("Asset change auth"), "pId": "accounts"},
    {"id": "terminal_node", "name": _("Terminal setting"), "pId": "view_setting"},
    {'id': "task_center", "name": _("Task Center"), "pId": "view_console"},
    {'id': "my_assets", "name": _("My assets"), "pId": "view_workbench"},
    {'id': "operation_center", "name": _('App ops'), "pId": "view_workbench"},
    {'id': "remote_application", "name": _("Applet"), "pId": "view_setting"},
]

# 将 model 放到其它节点下，而不是本来的 app 中
special_pid_mapper = {
    'common.permission': 'view_other',
    'assets.account': 'accounts',
    'assets.accounttemplate': 'accounts',
    'acls.commandfilteracl': 'perms',
    'acls.commandgroup': 'perms',
    'acls.loginacl': 'perms',
    'acls.loginassetacl': 'perms',
    'acls.connectmethodacl': 'perms',
    'xpack.account': 'cloud_import',
    'xpack.syncinstancedetail': 'cloud_import',
    'xpack.syncinstancetask': 'cloud_import',
    'xpack.syncinstancetaskexecution': 'cloud_import',
    'xpack.strategy': 'cloud_import',
    'xpack.strategyaction': 'cloud_import',
    'xpack.strategyrule': 'cloud_import',
    'terminal.applet': 'remote_application',
    'terminal.applethost': 'remote_application',
    'terminal.appletpublication': 'remote_application',
    'terminal.applethostdeployment': 'remote_application',
    'accounts.accountbackupautomation': "backup_account_node",
    'accounts.accountbackupexecution': "backup_account_node",
    "accounts.pushaccountautomation": "push_account_node",
    "accounts.view_pushaccountexecution": "push_account_node",
    "accounts.add_pushaccountexecution": "push_account_node",
    "accounts.gatheredaccount": "gather_account_node",
    "accounts.gatheraccountsautomation": "gather_account_node",
    "accounts.view_gatheraccountsexecution": "gather_account_node",
    "accounts.add_gatheraccountsexecution": "gather_account_node",
    "accounts.changesecretautomation": "asset_change_plan_node",
    "accounts.view_changesecretexecution": "asset_change_plan_node",
    "accounts.add_changesecretexecution": "asset_change_plan_node",
    "accounts.view_changesecretrecord": "asset_change_plan_node",
    'orgs.organization': 'view_setting',
    'settings.setting': 'view_setting',
    'terminal.terminal': 'terminal_node',
    'terminal.commandstorage': 'terminal_node',
    'terminal.replaystorage': 'terminal_node',
    'terminal.status': 'terminal_node',
    'terminal.task': 'terminal_node',
    'terminal.endpoint': 'terminal_node',
    'terminal.endpointrule': 'terminal_node',
    'audits.ftplog': 'terminal',
    'perms.view_myassets': 'my_assets',
    'ops.celerytask': 'task_center',
    'ops.view_celerytaskexecution': 'task_center',
    'ops.view_taskmonitor': 'task_center',
    'ops.adhocexecution': 'task_center',
    'ops.job': 'operation_center',
    'ops.adhoc': 'operation_center',
    'ops.playbook': 'operation_center',
    'ops.jobexecution': 'operation_center',
    "xpack.interface": "view_setting",
    "settings.change_terminal": "terminal_node",
    "settings.view_setting": "view_setting",
    "rbac.view_console": "view_console",
    "rbac.view_audit": "view_audit",
    'audits.usersession': 'view_audit',
    "rbac.view_workbench": "view_workbench",
    "rbac.view_webterminal": "view_workbench",
    "rbac.view_filemanager": "view_workbench",
    "rbac.view_systemtools": "view_workbench",
    'tickets.view_ticket': 'tickets'
}

verbose_name_mapper = {
    'orgs.organization': _("App organizations"),
    'tickets.comment': _("Ticket comment"),
    'tickets.view_ticket': _("Ticket"),
    'settings.setting': _("Common setting"),
    'rbac.view_permission': _('View permission tree'),
}

xpack_nodes = [
    'xpack', 'tickets', 'gather_account_node',
    'applications.remoteapp', "assets.accountbackupplan",
    "assets.accountbackupplanexecution",
    "rbac.orgrole", "rbac.orgrolebinding",
    'assets.gathereduser',

    'settings.change_interface', 'settings.change_sms',
    'users.invite_user', 'users.remove_user',
]


def _sort_action(node):
    if node.isParent:
        return ['zz', 0]

    action_resource = node.title.split('.')[-1]
    action, resource = action_resource.split('_', 2)
    action_value_mapper = {
        'view': 2,
        'add': 4,
        'change': 6,
        'delete': 8
    }
    v = action_value_mapper.get(action, 10)
    return [resource, v]


def sort_nodes(node):
    value = []

    if node.isParent:
        value.append(50)
    else:
        value.append(0)

    value.extend(_sort_action(node))
    return value


class CounterTree(Tree):
    def get_total_count(self, node):
        count = getattr(node, '_total_count', None)
        if count is not None:
            return count

        if not node.data.isParent:
            return 1

        count = 0
        children = self.children(node.identifier)
        for child in children:
            if child.data.isParent:
                count += self.get_total_count(child)
            else:
                count += 1
        node._total_count = count
        return count

    def get_checked_count(self, node):
        count = getattr(node, '_checked_count', None)
        if count is not None:
            return count

        if not node.data.isParent:
            if node.data.checked:
                return 1
            else:
                return 0

        count = 0
        children = self.children(node.identifier)
        for child in children:
            if child.data.isParent:
                count += self.get_checked_count(child)
            else:
                if child.data.checked:
                    count += 1
        node._checked_count = count
        return count

    def add_nodes_to_tree(self, ztree_nodes, retry=0):
        failed = []
        for node in ztree_nodes:
            pid = node.pId
            if retry == 2:
                pid = '$ROOT$'

            try:
                self.create_node(node.name, node.id, pid, data=node)
            except NodeIDAbsentError:
                failed.append(node)
        if retry > 2:
            return
        if failed:
            retry += 1
            return self.add_nodes_to_tree(failed, retry)


class PermissionTreeUtil:
    get_permissions: Callable
    action_mapper = {
        'add': _('Create'),
        'view': _('View'),
        'change': _('Update'),
        'delete': _('Delete')
    }
    action_icon = {
        'add': 'add',
        'view': 'view',
        'change': 'change',
        'delete': 'delete',
        'invite': 'invite',
        'match': 'match',
        'remove': 'remove'
    }

    def __init__(self, permissions, scope, check_disabled=False):
        self.permissions = self.prefetch_permissions(permissions)
        self.all_permissions = self.prefetch_permissions(
            Permission.get_permissions(scope)
        )
        self.check_disabled = check_disabled
        self.lang = get_language()

    @staticmethod
    def prefetch_permissions(perms):
        return perms.select_related('content_type') \
            .annotate(app=F('content_type__app_label')) \
            .annotate(model=F('content_type__model'))

    def create_apps_nodes(self):
        all_apps = apps.get_app_configs()
        apps_name_mapper = {
            app.name: app.verbose_name
            for app in all_apps if hasattr(app, 'verbose_name')
        }
        nodes = []

        for i in app_nodes_data:
            app = i['id']
            name = i.get('name') or apps_name_mapper.get(app, app)
            view = i.get('view', 'other')

            app_data = {
                'id': app,
                'name': name,
                'pId': view,
            }
            node = self._create_node(app_data, 'app', is_open=False)
            nodes.append(node)
        return nodes

    @staticmethod
    def _check_model_xpack(model_id):
        app, model = model_id.split('.', 2)
        if settings.XPACK_ENABLED:
            return True
        if app in xpack_nodes:
            return False
        if model_id in xpack_nodes:
            return False
        return True

    def _create_models_nodes(self):
        content_types = ContentType.objects.all()

        nodes = []
        for ct in content_types:
            model_id = '{}.{}'.format(ct.app_label, ct.model)
            if not self._check_model_xpack(model_id):
                continue

            # 获取 pid
            app = ct.app_label
            if model_id in special_pid_mapper:
                app = special_pid_mapper[model_id]

            # 获取 name
            name = f'{ct.name}'
            if model_id in verbose_name_mapper:
                name = verbose_name_mapper[model_id]

            node = self._create_node({
                'id': model_id,
                'name': name,
                'pId': app,
            }, 'model', is_open=False)
            nodes.append(node)
        return nodes

    def _get_permission_name_icon(self, p: Permission, content_types_name_mapper: dict):
        action, resource = p.codename.split('_', 1)
        icon = self.action_icon.get(action, 'file')
        name = verbose_name_mapper.get(p.app_label_codename)
        if name:
            return name, icon

        app_model = '%s.%s' % (p.content_type.app_label, resource)
        if self.lang == 'en':
            name = p.name
        # 因为默认的权限位是没有翻译的，所以我们要用 action + resource name 去拼
        elif action in self.action_mapper and app_model in content_types_name_mapper:
            action_name = self.action_mapper[action]
            resource_name = content_types_name_mapper[app_model]
            sep = ''
            name = '{}{}{}'.format(action_name, sep, resource_name)
        # 手动创建的 permission
        else:
            name = gettext(p.name)
        name = name.replace('Can ', '').replace('可以', '').capitalize()
        return name, icon

    def _create_perms_nodes(self):
        permissions_id = self.permissions.values_list('id', flat=True)
        nodes = []
        content_types = ContentType.objects.all()
        content_types_name_mapper = {ct.app_model: ct.name for ct in content_types}

        for p in self.all_permissions:
            model_id = f'{p.app}.{p.model}'
            if not self._check_model_xpack(model_id):
                continue
            title = p.app_label_codename
            if not settings.XPACK_ENABLED and title in xpack_nodes:
                continue

            # name 要特殊处理，解决 i18n 问题
            name, icon = self._get_permission_name_icon(p, content_types_name_mapper)
            if settings.DEBUG_DEV:
                name += '[{}]'.format(p.app_label_codename)

            pid = model_id
            # perm node 的特殊设置用的是 title，因为 id 是数字，不一致
            if title in special_pid_mapper:
                pid = special_pid_mapper[title]

            checked = p.id in permissions_id

            node = TreeNode(**{
                'id': p.id,
                'name': name,
                'title': title,
                'pId': pid,
                'isParent': False,
                'chkDisabled': self.check_disabled,
                'iconSkin': icon,
                'checked': checked,
                'open': False,
                'meta': {
                    'type': 'perm',
                }
            })
            nodes.append(node)
        return nodes

    def _create_node(self, data, tp, is_parent=True, is_open=True, icon='', checked=None):
        assert data.get('id')
        assert data.get('name')
        assert data.get('pId') is not None

        node_data = {
            'isParent': is_parent,
            'iconSkin': icon,
            'open': is_open,
            'chkDisabled': self.check_disabled,
            'checked': checked,
            'meta': {
                'type': tp,
            },
            **data
        }
        node_data['title'] = node_data['id']
        node = TreeNode(**node_data)
        if settings.DEBUG_DEV:
            node.name += ('[' + node.id + ']')
        if settings.DEBUG_DEV:
            node.name += ('-' + node.id)
        return node

    def _create_root_tree_node(self):
        node = self._create_node(root_node_data, 'root')
        return node

    def _create_views_node(self):
        nodes = []
        for view_data in view_nodes_data:
            data = {
                **view_data,
                'pId': '$ROOT$',
            }
            node = self._create_node(data, 'view', is_open=True)
            nodes.append(node)
        return nodes

    def _create_extra_nodes(self):
        nodes = []
        for data in extra_nodes_data:
            node = self._create_node(data, 'extra', is_open=False)
            nodes.append(node)
        return nodes

    @staticmethod
    def compute_nodes_count(ztree_nodes):
        tree = CounterTree()
        reverse_nodes = ztree_nodes[::-1]
        root = reverse_nodes[0]
        tree.create_node(root.name, root.id, data=root)
        tree.add_nodes_to_tree(reverse_nodes[1:])
        counter_nodes = tree.all_nodes()

        node_counts = {}
        for n in counter_nodes:
            if not n:
                continue
            total_count = tree.get_total_count(n)
            checked_count = tree.get_checked_count(n)
            node_counts[n.identifier] = [checked_count, total_count]

        nodes = []
        for node in ztree_nodes:
            counter = node_counts[node.id]
            if not counter:
                counter = [0, 0]
            checked_count, total_count = counter
            if total_count == 0:
                continue
            node.name += '({}/{})'.format(checked_count, total_count)
            if checked_count != 0:
                node.checked = True
            nodes.append(node)
        return nodes

    def create_tree_nodes(self):
        nodes = self._create_perms_nodes()
        nodes += self._create_models_nodes()
        nodes += self.create_apps_nodes()
        nodes += self._create_extra_nodes()
        nodes += self._create_views_node()
        nodes += [self._create_root_tree_node()]

        nodes = self.compute_nodes_count(nodes)
        nodes.sort(key=sort_nodes)
        return nodes

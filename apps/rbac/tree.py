#!/usr/bin/python
from collections import defaultdict
from typing import Callable
import os

from django.utils.translation import gettext_lazy as _, gettext, get_language
from django.conf import settings
from django.apps import apps
from django.db.models import F, Count

from common.tree import TreeNode
from .models import Permission, ContentType

DEBUG_DB = os.environ.get('DEBUG_DB', '0') == '1'

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
    {'id': 'view_workspace', 'name': _('Workspace view')},
    {'id': 'view_audit', 'name': _('Audit view')},
    {'id': 'view_setting', 'name': _('System setting')},
    {'id': 'view_other', 'name': _('Other')},
]

# 第三层 app 节点，手动创建
app_nodes_data = [
    {'id': 'users', 'view': 'view_console'},
    {'id': 'assets', 'view': 'view_console'},
    {'id': 'applications', 'view': 'view_console'},
    {'id': 'accounts', 'name': _('Accounts'), 'view': 'view_console'},
    {'id': 'perms', 'view': 'view_console'},
    {'id': 'acls', 'view': 'view_console'},
    {'id': 'ops', 'view': 'view_console'},
    {'id': 'terminal', 'name': _('Session audits'), 'view': 'view_audit'},
    {'id': 'audits', 'view': 'view_audit'},
    {'id': 'rbac', 'view': 'view_console'},
    {'id': 'settings', 'view': 'view_setting'},
    {'id': 'tickets', 'view': 'view_other'},
    {'id': 'authentication', 'view': 'view_other'},
]

# 额外其他节点，可以在不同的层次，需要指定父节点，可以将一些 model 归类到这个节点下面
extra_nodes_data = [
    {"id": "cloud_import", "name": _("Cloud import"), "pId": "assets"},
    {"id": "backup_account_node", "name": _("Backup account"), "pId": "accounts"},
    {"id": "gather_account_node", "name": _("Gather account"), "pId": "accounts"},
    {"id": "app_change_plan_node", "name": _("App change auth"), "pId": "accounts"},
    {"id": "asset_change_plan_node", "name": _("Asset change auth"), "pId": "accounts"},
    {"id": "terminal_node", "name": _("Terminal setting"), "pId": "view_setting"},
    {'id': "my_assets", "name": _("My assets"), "pId": "view_workspace"},
    {'id': "my_apps", "name": _("My apps"), "pId": "view_workspace"},
]

# 将 model 放到其它节点下，而不是本来的 app 中
special_pid_mapper = {
    'common.permission': 'view_other',
    "assets.authbook": "accounts",
    "applications.account": "accounts",
    'xpack.account': 'cloud_import',
    'xpack.syncinstancedetail': 'cloud_import',
    'xpack.syncinstancetask': 'cloud_import',
    'xpack.syncinstancetaskexecution': 'cloud_import',
    'assets.accountbackupplan': "backup_account_node",
    'assets.accountbackupplanexecution': "backup_account_node",
    'xpack.applicationchangeauthplan': 'app_change_plan_node',
    'xpack.applicationchangeauthplanexecution': 'app_change_plan_node',
    'xpack.applicationchangeauthplantask': 'app_change_plan_node',
    'xpack.changeauthplan': 'asset_change_plan_node',
    'xpack.changeauthplanexecution': 'asset_change_plan_node',
    'xpack.changeauthplantask': 'asset_change_plan_node',
    "assets.gathereduser": "gather_account_node",
    'xpack.gatherusertask': 'gather_account_node',
    'xpack.gatherusertaskexecution': 'gather_account_node',
    'orgs.organization': 'view_setting',
    'settings.setting': 'view_setting',
    'terminal.terminal': 'terminal_node',
    'terminal.commandstorage': 'terminal_node',
    'terminal.replaystorage': 'terminal_node',
    'terminal.status': 'terminal_node',
    'terminal.task': 'terminal_node',
    'audits.ftplog': 'terminal',
    'perms.view_myassets': 'my_assets',
    'perms.view_myapps': 'my_apps',
    'ops.add_commandexecution': 'view_workspace',
    'ops.view_commandexecution': 'audits',
    "perms.view_mykubernetsapp": "my_apps",
    "perms.connect_mykubernetsapp": "my_apps",
    "perms.view_myremoteapp": "my_apps",
    "perms.connect_myremoteapp": "my_apps",
    "perms.view_mydatabaseapp": "my_apps",
    "perms.connect_mydatabaseapp": "my_apps",
    "xpack.interface": "view_setting",
    "settings.change_terminal": "terminal_node",
    "settings.view_setting": "view_setting",
    "rbac.view_console": "view_console",
    "rbac.view_audit": "view_audit",
    "rbac.view_workspace": "view_workspace",
    "rbac.view_webterminal": "view_workspace",
    "rbac.view_filemanager": "view_workspace",
    'tickets.view_ticket': 'tickets'
}

verbose_name_mapper = {
    'orgs.organization': _("App organizations"),
    'tickets.comment': _("Ticket comment"),
    'tickets.view_ticket': _("Ticket"),
    'settings.setting': _("Common setting"),
    'rbac.view_permission': _('View permission tree'),
    'ops.add_commandexecution': _('Execute batch command')
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
        self.total_counts = defaultdict(int)
        self.checked_counts = defaultdict(int)
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
            total_count = self.total_counts[app]
            checked_count = self.checked_counts[app]
            if total_count == 0:
                continue
            self.total_counts[view] += total_count
            self.checked_counts[view] += checked_count
            node = self._create_node(
                app_data, total_count, checked_count,
                'app', is_open=False
            )
            nodes.append(node)
        return nodes

    def _get_model_counts_mapper(self):
        model_counts = self.all_permissions \
            .values('model', 'app', 'content_type') \
            .order_by('content_type') \
            .annotate(count=Count('content_type'))
        model_check_counts = self.permissions \
            .values('content_type', 'model') \
            .order_by('content_type') \
            .annotate(count=Count('content_type'))
        model_counts_mapper = {
            i['content_type']: i['count']
            for i in model_counts
        }
        model_check_counts_mapper = {
            i['content_type']: i['count']
            for i in model_check_counts
        }
        return model_counts_mapper, model_check_counts_mapper

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

            total_count = self.total_counts[model_id]
            checked_count = self.checked_counts[model_id]
            if total_count == 0:
                continue

            # 获取 pid
            app = ct.app_label
            if model_id in special_pid_mapper:
                app = special_pid_mapper[model_id]
            self.total_counts[app] += total_count
            self.checked_counts[app] += checked_count

            # 获取 name
            name = f'{ct.name}'
            if model_id in verbose_name_mapper:
                name = verbose_name_mapper[model_id]

            node = self._create_node({
                'id': model_id,
                'name': name,
                'pId': app,
            }, total_count, checked_count, 'model', is_open=False)
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
            if DEBUG_DB:
                name += '[{}]'.format(p.app_label_codename)

            pid = model_id
            # perm node 的特殊设置用的是 title，因为 id 是数字，不一致
            if title in special_pid_mapper:
                pid = special_pid_mapper[title]

            self.total_counts[pid] += 1
            checked = p.id in permissions_id
            if checked:
                self.checked_counts[pid] += 1

            node = TreeNode(**{
                'id': p.id,
                'name': name,
                'title': title,
                'pId': pid,
                'isParent': False,
                'chkDisabled': self.check_disabled,
                'iconSkin': icon,
                'checked': p.id in permissions_id,
                'open': False,
                'meta': {
                    'type': 'perm',
                }
            })
            nodes.append(node)
        return nodes

    def _create_node(self, data, total_count, checked_count, tp,
                     is_parent=True, is_open=True, icon='', checked=None):
        assert data.get('id')
        assert data.get('name')
        assert data.get('pId') is not None
        if checked is None:
            checked = total_count == checked_count
        node_data = {
            'isParent': is_parent,
            'iconSkin': icon,
            'open': is_open,
            'chkDisabled': self.check_disabled,
            'checked': checked,
            'meta': {
                'type':  tp,
            },
            **data
        }
        node_data['title'] = node_data['id']
        node = TreeNode(**node_data)
        if DEBUG_DB:
            node.name += ('[' + node.id + ']')
        if DEBUG_DB:
            node.name += ('-' + node.id)
        node.name += f'({checked_count}/{total_count})'
        return node

    def _create_root_tree_node(self):
        total_count = self.all_permissions.count()
        checked_count = self.permissions.count()
        node = self._create_node(root_node_data, total_count, checked_count, 'root')
        return node

    def _create_views_node(self):
        nodes = []
        for view_data in view_nodes_data:
            view = view_data['id']
            data = {
                **view_data,
                'pId': '$ROOT$',
            }
            total_count = self.total_counts[view]
            checked_count = self.checked_counts[view]
            if total_count == 0:
                continue
            node = self._create_node(data, total_count, checked_count, 'view', is_open=True)
            nodes.append(node)
        return nodes

    def _create_extra_nodes(self):
        nodes = []
        for data in extra_nodes_data:
            i = data['id']
            pid = data['pId']
            checked_count = self.checked_counts[i]
            total_count = self.total_counts[i]
            if total_count == 0:
                continue
            self.total_counts[pid] += total_count
            self.checked_counts[pid] += checked_count
            node = self._create_node(
                data, total_count, checked_count,
                'extra', is_open=False
            )
            nodes.append(node)
        return nodes

    def create_tree_nodes(self):
        nodes = self._create_perms_nodes()
        nodes += self._create_models_nodes()
        nodes += self.create_apps_nodes()
        nodes += self._create_extra_nodes()
        nodes += self._create_views_node()
        nodes += [self._create_root_tree_node()]

        nodes.sort(key=sort_nodes)
        return nodes

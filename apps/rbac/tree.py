#!/usr/bin/python
from collections import defaultdict
from typing import Callable

from django.utils.translation import gettext_lazy as _, gettext
from django.conf import settings
from django.apps import apps
from django.db.models import F, Count
from django.utils.translation import ugettext

from .models import Permission, ContentType
from common.tree import TreeNode

root_node_data = {
    'id': '$ROOT$',
    'name': _('All permissions'),
    'title': _('All permissions'),
    'pId': '',
}

view_nodes_data = [
    {
        'id': 'view_console',
        'name': _('Console view'),
    },
    {
        'id': 'view_workspace',
        'name': _('Workspace view'),
    },
    {
        'id': 'view_audit',
        'name': _('Audit view'),
    },
    {
        'id': 'view_setting',
        'name': _('System setting'),
    },
    {
        'id': 'view_other',
        'name': _('Other'),
    }
]

app_nodes_data = [
    {
        'id': 'users',
        'view': 'view_console',
    },
    {
        'id': 'assets',
        'view': 'view_console',
    },
    {
        'id': 'applications',
        'view': 'view_console',
    },
    {
        'id': 'accounts',
        'name': _('Accounts'),
        'view': 'view_console',
    },
    {
        'id': 'perms',
        'view': 'view_console',
    },
    {
        'id': 'acls',
        'view': 'view_console',
    },
    {
        'id': 'ops',
        'view': 'view_console',
    },
    {
        'id': 'terminal',
        'name': _('Session audits'),
        'view': 'view_audit',
    },
    {
        'id': 'audits',
        'view': 'view_audit',
    },
    {
        'id': 'rbac',
        'view': 'view_console'
    },
    {
        'id': 'settings',
        'view': 'view_setting'
    },
    {
        'id': 'tickets',
        'view': 'view_other',
    },
    {
        'id': 'authentication',
        'view': 'view_other'
    }
]

extra_nodes_data = [
    {
        "id": "cloud_import",
        "name": _("Cloud import"),
        "pId": "assets",
    },
    {
        "id": "backup_account_node",
        "name": _("Backup account"),
        "pId": "accounts"
    },
    {
        "id": "gather_account_node",
        "name": _("Gather account"),
        "pId": "accounts",
    },
    {
        "id": "app_change_plan_node",
        "name": _("App change auth"),
        "pId": "accounts"
    },
    {
        "id": "asset_change_plan_node",
        "name": _("Asset change auth"),
        "pId": "accounts"
    },
    {
        "id": "terminal_node",
        "name": _("Terminal setting"),
        "pId": "view_setting"
    }
]

special_model_pid_mapper = {
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
}

model_verbose_name_mapper = {
    'orgs.organization': _("App organizations"),
}

xpack_required = [
    'accounts', 'rbac.'
]


class PermissionTreeUtil:
    get_permissions: Callable

    def __init__(self, permissions, scope, check_disabled=False):
        self.permissions = self.prefetch_permissions(permissions)
        self.all_permissions = self.prefetch_permissions(
            Permission.get_permissions(scope)
        )
        self.check_disabled = check_disabled
        self.total_counts = defaultdict(int)
        self.checked_counts = defaultdict(int)

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

    def _create_models_nodes(self):
        content_types = ContentType.objects.all()
        total_counts_mapper, checked_counts_mapper = self._get_model_counts_mapper()

        nodes = []
        for ct in content_types:
            total_count = total_counts_mapper.get(ct.id, 0)
            checked_count = checked_counts_mapper.get(ct.id, 0)
            if total_count == 0:
                continue

            model_id = '{}.{}'.format(ct.app_label, ct.model)
            # 获取 pid
            app = ct.app_label
            if special_model_pid_mapper.get(model_id):
                app = special_model_pid_mapper[model_id]
            self.total_counts[app] += total_count
            self.checked_counts[app] += checked_count

            # 获取 name
            name = f'{ct.name}'
            if model_verbose_name_mapper.get(model_id):
                name = model_verbose_name_mapper[model_id]

            node = self._create_node({
                'id': model_id,
                'name': name,
                'pId': app,
            }, total_count, checked_count, 'model', is_open=False)
            nodes.append(node)
        return nodes

    @staticmethod
    def _get_permission_name(p, content_types_name_mapper):
        code_name = p.codename
        action_mapper = {
            'add': ugettext('Create'),
            'view': ugettext('View'),
            'change': ugettext('Update'),
            'delete': ugettext('Delete')
        }
        name = ''
        ct = ''
        if 'add_' in p.codename:
            name = action_mapper['add']
            ct = code_name.replace('add_', '')
        elif 'view_' in p.codename:
            name = action_mapper['view']
            ct = code_name.replace('view_', '')
        elif 'change_' in p.codename:
            name = action_mapper['change']
            ct = code_name.replace('change_', '')
        elif 'delete' in code_name:
            name = action_mapper['delete']
            ct = code_name.replace('delete_', '')

        if ct in content_types_name_mapper:
            name += content_types_name_mapper[ct]
        else:
            name = gettext(p.name)
            name = name.replace('Can ', '').replace('可以', '')
        return name

    def _create_perms_nodes(self):
        permissions_id = self.permissions.values_list('id', flat=True)
        nodes = []
        content_types = ContentType.objects.all()
        content_types_name_mapper = {ct.model: ct.name for ct in content_types}

        for p in self.all_permissions:
            model_id = f'{p.app}.{p.model}'
            name = self._get_permission_name(p, content_types_name_mapper)
            if settings.DEBUG:
                name += '({})'.format(p.app_label_codename)

            node = TreeNode(**{
                'id': p.id,
                'name': name,
                'title': p.name,
                'pId': model_id,
                'isParent': False,
                'chkDisabled': self.check_disabled,
                'iconSkin': 'file',
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
        if not node_data.get('title'):
            node_data['title'] = node_data['name']
        node = TreeNode(**node_data)
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
            node = self._create_node(data, total_count, checked_count, 'view')
            nodes.append(node)
        return nodes
    
    def _create_extra_nodes(self):
        nodes = []
        for data in extra_nodes_data:
            i = data['id']
            pid = data['pId']
            checked_count = self.checked_counts[i]
            total_count = self.total_counts[i]
            self.total_counts[pid] += total_count
            self.checked_counts[pid] += checked_count
            node = self._create_node(
                data, total_count, checked_count,
                'extra', is_open=False
            )
            nodes.append(node)

        return nodes

    def create_tree_nodes(self):
        nodes = [self._create_root_tree_node()]
        perms_nodes = self._create_perms_nodes()
        models_nodes = self._create_models_nodes()
        apps_nodes = self.create_apps_nodes()
        views_nodes = self._create_views_node()
        extra_nodes = self._create_extra_nodes()

        nodes += views_nodes + apps_nodes + models_nodes + perms_nodes + extra_nodes
        return nodes

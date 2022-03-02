#!/usr/bin/python
from django.utils.translation import gettext_lazy as _
from typing import Callable
from django.apps import apps
from django.db.models import F, Count
from django.utils.translation import ugettext

from .models import Permission, ContentType
from common.tree import TreeNode

perm_app_nodes = [
    {
        'app': 'users',
    },
    {
        'app': 'assets'
    },
    {
        'app': 'applications'
    },
    {
        'app': 'accounts',
        'full_name': _('Account')
    },
    {
       'app': 'perms'
    },
    {
       'app': 'acls'
    },
    {
       'app': 'ops'
    },
    {
        'app': 'sessions'
    },
    {
        'app': 'audits'
    },
    {
        'app': 'orgs'
    },
    {
        'app': 'rbac',
    },
    {
        'app': 'settings'
    },
    {
        'app': 'tickets'
    },
    {
        'app': 'authentication'
    },
    {
        'app': 'menu',
        'full_name': _("Menu permission"),
    },
]

special_model_app_mapper = {
    'common.permission': ''
}

special_code_models_mapper = {

}


class PermissionTreeUtil:
    get_permissions: Callable

    def __init__(self, permissions, scope, check_disabled=False):
        self.permissions = self.prefetch_permissions(permissions)
        self.all_permissions = self.prefetch_permissions(
            Permission.get_permissions(scope)
        )
        self.check_disabled = check_disabled

    @staticmethod
    def prefetch_permissions(perms):
        return perms.select_related('content_type') \
            .annotate(app=F('content_type__app_label')) \
            .annotate(model=F('content_type__model'))

    def _create_apps_tree_nodes(self):
        app_counts = self.all_permissions.values('app') \
            .order_by('app').annotate(count=Count('app'))
        app_checked_counts = self.permissions.values('app') \
            .order_by('app').annotate(count=Count('app'))
        app_checked_counts_mapper = {
            i['app']: i['count']
            for i in app_checked_counts
        }
        all_apps = apps.get_app_configs()
        apps_name_mapper = {
            app.name: app.verbose_name
            for app in all_apps if hasattr(app, 'verbose_name')
        }
        nodes = []

        for i in app_counts:
            app = i['app']
            total_counts = i['count']
            check_counts = app_checked_counts_mapper.get(app, 0)
            name = apps_name_mapper.get(app, app)
            full_name = f'{name}({check_counts}/{total_counts})'

            node = TreeNode(**{
                'id': app,
                'name': full_name,
                'title': name,
                'pId': '$ROOT$',
                'isParent': True,
                'open': False,
                'chkDisabled': self.check_disabled,
                'checked': total_counts == check_counts,
                'iconSkin': '',
                'meta': {
                    'type': 'app',
                }
            })
            nodes.append(node)
        return nodes

    def _create_models_tree_nodes(self):
        content_types = ContentType.objects.all()

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

        nodes = []
        for ct in content_types:
            total_counts = model_counts_mapper.get(ct.id, 0)
            if total_counts == 0:
                continue
            check_counts = model_check_counts_mapper.get(ct.id, 0)
            model_id = f'{ct.app_label}_{ct.model}'
            name = f'{ct.name}({check_counts}/{total_counts})'
            node = TreeNode(**{
                'id': model_id,
                'name': name,
                'title': name,
                'pId': ct.app_label,
                'chkDisabled': self.check_disabled,
                'isParent': True,
                'open': False,
                'checked': total_counts == check_counts,
                'meta': {
                    'type': 'model',
                }
            })
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
            name = p.name
        return name

    def _create_perms_tree_nodes(self):
        permissions_id = self.permissions.values_list('id', flat=True)
        nodes = []
        content_types = ContentType.objects.all()
        content_types_name_mapper = {ct.model: ct.name for ct in content_types}
        for p in self.all_permissions:
            model_id = f'{p.app}_{p.model}'
            name = self._get_permission_name(p, content_types_name_mapper)

            node = TreeNode(**{
                'id': p.id,
                'name': name + '({})'.format(p.app_label_codename),
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

    def _create_root_tree_node(self):
        total_counts = self.all_permissions.count()
        check_counts = self.permissions.count()
        node = TreeNode(**{
            'id': '$ROOT$',
            'name': f'所有权限({check_counts}/{total_counts})',
            'title': '所有权限',
            'pId': '',
            'chkDisabled': self.check_disabled,
            'isParent': True,
            'checked': total_counts == check_counts,
            'open': True,
            'meta': {
                'type': 'root',
            }
        })
        return node

    def create_tree_nodes(self):
        nodes = [self._create_root_tree_node()]
        apps_nodes = self._create_apps_tree_nodes()
        models_nodes = self._create_models_tree_nodes()
        perms_nodes = self._create_perms_tree_nodes()

        nodes += apps_nodes + models_nodes + perms_nodes
        return nodes


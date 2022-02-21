from typing import Callable

from django.db.models import F, Count, Q
from django.apps import apps
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import Permission as DjangoPermission
from django.contrib.auth.models import ContentType as DjangoContentType

from common.tree import TreeNode
from .. import const

Scope = const.Scope

__all__ = ['Permission', 'ContentType']


class ContentType(DjangoContentType):
    class Meta:
        proxy = True


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
        app_counts = self.all_permissions.values('app')\
            .order_by('app').annotate(count=Count('app'))
        app_checked_counts = self.permissions.values('app')\
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


class Permission(DjangoPermission):
    """ 权限类 """
    class Meta:
        proxy = True
        verbose_name = _('Permission')

    @classmethod
    def to_perms(cls, queryset):
        perms = queryset.values_list(
            'content_type__app_label', 'codename'
        )
        perms = list(set(["%s.%s" % (ct, codename) for ct, codename in perms]))
        return sorted(perms)

    @property
    def app_label_codename(self):
        return '%s.%s' % (self.content_type.app_label, self.codename)

    @classmethod
    def get_define_permissions_q(cls, defines):
        """
        :param defines: [(app, model, codename),]
        :return:
        """
        if not defines:
            return None
        q = Q()

        for define in defines:
            app_label, model, actions, resource, *args = list(define)
            kwargs = {}
            if app_label != '*':
                kwargs['content_type__app_label'] = app_label
            if model != '*':
                kwargs['content_type__model'] = model

            actions_list = [a.strip() for a in actions.split(',')]
            actions_regex = '|'.join(actions_list)
            if actions == '*' and resource == '*':
                pass
            elif actions == '*' and resource != '*':
                kwargs['codename__iregex'] = r'[a-z]+_{}'.format(resource)
            elif actions != '*' and resource == '*':
                kwargs['codename__iregex'] = r'({})_\w+'.format(actions_regex)
            else:
                kwargs['codename__iregex'] = r'({})_{}'.format(actions_regex, resource)
            q |= Q(**kwargs)
        return q

    @classmethod
    def clean_permissions(cls, permissions, scope=Scope.system):
        if scope == Scope.org:
            excludes = const.org_exclude_permissions
        else:
            excludes = const.system_exclude_permissions
        q = cls.get_define_permissions_q(excludes)
        if q:
            permissions = permissions.exclude(q)
        return permissions

    @staticmethod
    def create_tree_nodes(permissions, scope, check_disabled=False):
        util = PermissionTreeUtil(permissions, scope, check_disabled)
        return util.create_tree_nodes()

    @classmethod
    def get_permissions(cls, scope):
        permissions = cls.objects.all()
        permissions = cls.clean_permissions(permissions, scope=scope)
        return permissions



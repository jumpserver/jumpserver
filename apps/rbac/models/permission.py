import uuid
from typing import Callable

from django.db import models
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


class PermissionTreeMixin:
    get_permissions: Callable

    @classmethod
    def _create_apps_tree_nodes(cls, all_permissions, permissions, check_disabled=False):
        app_counts = all_permissions.values('app').order_by('app').annotate(count=Count('app'))
        app_checked_counts = permissions.values('app').order_by('app').annotate(count=Count('app'))
        app_checked_counts_mapper = {i['app']: i['count'] for i in app_checked_counts}
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
                'chkDisabled': check_disabled,
                'checked': total_counts == check_counts,
                'iconSkin': '',
                'meta': {
                    'type': 'app',
                }
            })
            nodes.append(node)
        return nodes

    @classmethod
    def _create_models_tree_nodes(cls, all_permissions, permissions, check_disabled=False):
        content_types = ContentType.objects.all()

        model_counts = all_permissions \
            .values('model', 'app', 'content_type') \
            .order_by('content_type') \
            .annotate(count=Count('content_type'))
        model_check_counts = permissions \
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
                # 'name': name + "||" + ct.model,
                'title': name,
                'pId': ct.app_label,
                'chkDisabled': check_disabled,
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

    @classmethod
    def _create_perms_tree_nodes(cls, all_permissions, permissions, check_disabled=False):
        permissions_id = permissions.values_list('id', flat=True)
        nodes = []
        content_types = ContentType.objects.all()
        content_types_name_mapper = {ct.model: ct.name for ct in content_types}
        for p in all_permissions:
            model_id = f'{p.app}_{p.model}'
            name = cls._get_permission_name(p, content_types_name_mapper)

            node = TreeNode(**{
                'id': p.id,
                'name': name,
                'title': p.name,
                'pId': model_id,
                'isParent': False,
                'chkDisabled': check_disabled,
                'iconSkin': 'file',
                'checked': p.id in permissions_id,
                'open': False,
                'meta': {
                    'type': 'perm',
                }
            })
            nodes.append(node)
        return nodes

    @staticmethod
    def _create_root_tree_node(all_permissions, permissions, check_disabled=False):
        total_counts = all_permissions.count()
        check_counts = permissions.count()
        node = TreeNode(**{
            'id': '$ROOT$',
            'name': f'所有权限({check_counts}/{total_counts})',
            'title': '所有权限',
            'pId': '',
            'chkDisabled': check_disabled,
            'isParent': True,
            'checked': total_counts == check_counts,
            'open': True,
            'meta': {
                'type': 'root',
            }
        })
        return node

    @classmethod
    def create_tree_nodes(cls, permissions, scope='org', check_disabled=False):
        perms_using = [cls.get_permissions(scope), permissions]
        for i, perms in enumerate(perms_using):
            perms_using[i] = perms.select_related('content_type') \
                .annotate(app=F('content_type__app_label')) \
                .annotate(model=F('content_type__model'))

        all_permissions, permissions = perms_using
        nodes = [cls._create_root_tree_node(all_permissions, permissions, check_disabled)]
        apps_nodes = cls._create_apps_tree_nodes(all_permissions, permissions, check_disabled)
        models_nodes = cls._create_models_tree_nodes(all_permissions, permissions, check_disabled)
        perms_nodes = cls._create_perms_tree_nodes(all_permissions, permissions, check_disabled)

        nodes += apps_nodes + models_nodes + perms_nodes
        return nodes


class Permission(DjangoPermission, PermissionTreeMixin):
    """ 权限类 """
    class Meta:
        proxy = True
        verbose_name = _('Permission')

    @property
    def app_label_codename(self):
        return '%s.%s' % (self.content_type.app_label, self.codename)

    @classmethod
    def get_define_permissions_q(cls, defines):
        """
        :param defines: [(app, model, codename),]
        :return:
        """
        q = Q()
        for app_label, model, code_name in defines:
            kwargs = {}
            if app_label != '*':
                kwargs['content_type__app_label'] = app_label
            if model != '*':
                kwargs['content_type__model'] = model
            if code_name != '*':
                kwargs['codename'] = code_name
            q |= Q(**kwargs)
        return q

    @classmethod
    def clean_permissions(cls, permissions, scope=Scope.system):
        excludes = list(const.exclude_permissions)
        if scope == Scope.org:
            excludes.extend(const.system_scope_permissions)

        q = cls.get_define_permissions_q(excludes)
        permissions = permissions.exclude(q)
        return permissions

    @classmethod
    def get_permissions(cls, scope):
        # TODO: 根据类型过滤出对应的权限位并返回
        permissions = cls.objects.all()
        permissions = cls.clean_permissions(permissions, scope=scope)
        return permissions


class ExtraPermission(models.Model):
    """ 附加权限位类，用来定义无资源类的权限，不做实体资源 """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)

    class Meta:
        default_permissions = []
        verbose_name = _('Extra permission')
        permissions = [
            ('view_adminview', _('Can view admin view')),
            ('view_auditview', _('Can view audit view')),
            ('view_userview', _('Can view user view')),
        ]

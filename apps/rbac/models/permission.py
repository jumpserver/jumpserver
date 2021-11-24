import uuid
from typing import Callable
from django.db import models
from django.db.models import F, Count
from django.utils.translation import ugettext_lazy as _
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
    def create_apps_tree_nodes(cls, all_permissions, permissions):
        app_counts = all_permissions.values('app').order_by('app').annotate(count=Count('app'))
        app_checked_counts = permissions.values('app').order_by('app').annotate(count=Count('app'))
        app_checked_counts_mapper = {i['app']: i['count'] for i in app_checked_counts}

        nodes = []
        for i in app_counts:
            app = i['app']
            total_counts = i['count']
            check_counts = app_checked_counts_mapper.get(app, 0)
            name = f'{app}({check_counts}/{total_counts})'

            node = TreeNode(**{
                'id': app,
                'name': name,
                'title': app,
                'pId': '$ROOT$',
                'isParent': True,
                'open': False,
                'checked': total_counts == check_counts,
                # 'halfCheck': check_counts != 0,
                'iconSkin': '',
                'meta': {
                    'type': 'app',
                }
            })
            nodes.append(node)
        return nodes

    @classmethod
    def create_models_tree_nodes(cls, all_permissions, permissions):
        model_counts = all_permissions \
            .values('model', 'app', 'model_id') \
            .order_by('model_id') \
            .annotate(count=Count('model_id'))
        model_check_counts = permissions \
            .values('model_id', 'model') \
            .order_by('model_id') \
            .annotate(count=Count('model_id'))
        model_check_counts_mapper = {
            i['model_id']: i['count']
            for i in model_check_counts
        }

        nodes = []
        for i in model_counts:
            app = i['app']
            model_id = i['model_id']
            model = i['model']
            total_counts = i['count']
            check_counts = model_check_counts_mapper.get(model_id, 0)
            name = f'{model}({check_counts}/{total_counts})'
            node = TreeNode(**{
                'id': "model_{}".format(model_id),
                'name': name,
                'title': model,
                'pId': app,
                'isParent': True,
                'open': False,
                'checked': total_counts == check_counts,
                'meta': {
                    'type': 'model',
                }
            })
            nodes.append(node)
        return nodes

    @classmethod
    def create_permissions_tree_nodes(cls, all_permissions, permissions):
        permissions_id = permissions.values_list('id', flat=True)
        nodes = []
        for p in all_permissions:
            node = TreeNode(**{
                'id': p.id,
                'name': p.name,
                'title': p.name,
                'pId': f'model_{p.model_id}',
                'isParent': False,
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
    def create_root_tree_node(all_permissions, permissions):
        total_counts = all_permissions.count()
        check_counts = permissions.count()
        node = TreeNode(**{
            'id': '$ROOT$',
            'name': f'所有权限({check_counts}/{total_counts})',
            'title': '所有权限',
            'pId': '',
            'isParent': True,
            'checked': total_counts == check_counts,
            'open': True,
            'meta': {
                'type': 'root',
            }
        })
        return node

    @classmethod
    def create_tree_nodes(cls, permissions, scope='org'):
        perms_using = [cls.get_permissions(scope), permissions]
        for i, perms in enumerate(perms_using):
            perms_using[i] = perms.select_related('content_type') \
                .annotate(app=F('content_type__app_label')) \
                .annotate(model=F('content_type__model')) \
                .annotate(model_id=F('content_type__id'))

        all_permissions, permissions = perms_using
        nodes = [cls.create_root_tree_node(all_permissions, permissions)]
        apps_nodes = cls.create_apps_tree_nodes(all_permissions, permissions)
        models_nodes = cls.create_models_tree_nodes(all_permissions, permissions)
        permissions_nodes = cls.create_permissions_tree_nodes(all_permissions, permissions)

        nodes += apps_nodes + models_nodes + permissions_nodes
        return nodes


class Permission(DjangoPermission, PermissionTreeMixin):
    """ 权限类 """
    class Meta:
        proxy = True

    @property
    def app_label_codename(self):
        return '%s.%s' % (self.content_type.app_label, self.codename)

    @classmethod
    def clean_permissions(cls, permissions, scope=Scope.system):
        excludes = list(const.exclude_permissions)
        if scope == Scope.org:
            excludes.extend(const.system_scope_permissions)

        for app_label, code_name in excludes:
            permissions = permissions.exclude(
                codename=code_name,
                content_type__app_label=app_label
            )
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
        permissions = [
            ('view_adminview', _('Can view admin view')),
            ('view_auditview', _('Can view audit view')),
            ('view_userview', _('Can view user view')),
        ]

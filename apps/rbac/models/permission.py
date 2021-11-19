import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import Permission as DjangoPermission
from django.contrib.auth.models import ContentType as DjangoContentType

from common.tree import TreeNode

__all__ = ['Permission', 'ContentType']


class ContentType(DjangoContentType):

    class Meta:
        proxy = True


class Permission(DjangoPermission):
    """ 权限类 """
    class Meta:
        proxy = True

    @property
    def app_label_codename(self):
        return '%s.%s' % (self.content_type.app_label, self.codename)

    @classmethod
    def get_permissions(cls, scope):
        # TODO: 根据类型过滤出对应的权限位并返回
        return cls.objects.all()

    @classmethod
    def create_app_tree_node(cls, app_id, app_label):
        node = TreeNode(**{
            'id': app_id,
            'name': app_label,
            'title': app_label,
            'pId': '',
            'isParent': True,
            'open': False,
            'iconSkin': '',
            'meta': {
                'type': 'app',
            }
        })
        return node

    @classmethod
    def create_model_tree_node(cls, model_id, model_name, pid):
        node = TreeNode(**{
            'id': model_id,
            'name': model_name,
            'title': model_name,
            'pId': pid,
            'isParent': True,
            'open': False,
            'meta': {
                'type': 'model',
            }
        })
        return node

    @classmethod
    def create_permission_tree_node(cls, p, pid):
        node = TreeNode(**{
            'id': p.id,
            'name': p.name,
            'title': p.name,
            'pId': pid,
            'isParent': False,
            'iconSkin': 'file',
            'open': False,
            'meta': {
                'type': 'permission',
            }
        })
        return node

    @classmethod
    def create_tree_nodes(cls, queryset):
        node_mapper = {}

        for p in queryset:
            # 创建 app 节点
            app_node_id = p.content_type.app_label
            if app_node_id not in node_mapper:
                node_mapper[app_node_id] = cls.create_app_tree_node(app_node_id, app_node_id)

            # 创建 Model 节点
            model_node_id = app_node_id + '_' + p.content_type.model
            model_name = p.content_type.model
            if model_node_id not in node_mapper:
                node_mapper[model_node_id] = cls.create_model_tree_node(model_node_id, model_name, app_node_id)

            # 创建权限位节点
            node_mapper[p.id] = cls.create_permission_tree_node(p, model_node_id)
        return node_mapper.values()


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

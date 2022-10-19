from collections import defaultdict
from urllib.parse import urlencode, parse_qsl

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from orgs.mixins.models import OrgModelMixin
from common.mixins import CommonModelMixin
from common.tree import TreeNode
from common.utils import is_uuid
from assets.models import Asset, SystemUser

from .. import const


class ApplicationTreeNodeMixin:
    id: str
    name: str
    type: str
    category: str
    attrs: dict

    @staticmethod
    def create_tree_id(pid, type, v):
        i = dict(parse_qsl(pid))
        i[type] = v
        tree_id = urlencode(i)
        return tree_id

    @classmethod
    def create_choice_node(cls, c, id_, pid, tp, opened=False, counts=None,
                           show_empty=True, show_count=True):
        count = counts.get(c.value, 0)
        if count == 0 and not show_empty:
            return None
        label = c.label
        if count is not None and show_count:
            label = '{} ({})'.format(label, count)
        data = {
            'id': id_,
            'name': label,
            'title': label,
            'pId': pid,
            'isParent': bool(count),
            'open': opened,
            'iconSkin': '',
            'meta': {
                'type': tp,
                'data': {
                    'name': c.name,
                    'value': c.value
                }
            }
        }
        return TreeNode(**data)

    @classmethod
    def create_root_tree_node(cls, queryset, show_count=True):
        count = queryset.count() if show_count else None
        root_id = 'applications'
        root_name = _('Applications')
        if count is not None and show_count:
            root_name = '{} ({})'.format(root_name, count)
        node = TreeNode(**{
            'id': root_id,
            'name': root_name,
            'title': root_name,
            'pId': '',
            'isParent': True,
            'open': True,
            'iconSkin': '',
            'meta': {
                'type': 'applications_root',
            }
        })
        return node

    @classmethod
    def create_category_tree_nodes(cls, pid, counts=None, show_empty=True, show_count=True):
        nodes = []
        categories = const.AppType.category_types_mapper().keys()
        for category in categories:
            if not settings.XPACK_ENABLED and const.AppCategory.is_xpack(category):
                continue
            i = cls.create_tree_id(pid, 'category', category.value)
            node = cls.create_choice_node(
                category, i, pid=pid, tp='category',
                counts=counts, opened=False, show_empty=show_empty,
                show_count=show_count
            )
            if not node:
                continue
            nodes.append(node)
        return nodes

    @classmethod
    def create_types_tree_nodes(cls, pid, counts, show_empty=True, show_count=True):
        nodes = []
        temp_pid = pid
        type_category_mapper = const.AppType.type_category_mapper()
        types = const.AppType.type_category_mapper().keys()

        for tp in types:
            if not settings.XPACK_ENABLED and const.AppType.is_xpack(tp):
                continue
            category = type_category_mapper.get(tp)
            pid = cls.create_tree_id(pid, 'category', category.value)
            i = cls.create_tree_id(pid, 'type', tp.value)
            node = cls.create_choice_node(
                tp, i, pid, tp='type', counts=counts, opened=False,
                show_empty=show_empty, show_count=show_count
            )
            pid = temp_pid
            if not node:
                continue
            nodes.append(node)
        return nodes

    @staticmethod
    def get_tree_node_counts(queryset):
        counts = defaultdict(int)
        values = queryset.values_list('type', 'category')
        for i in values:
            tp = i[0]
            category = i[1]
            counts[tp] += 1
            counts[category] += 1
        return counts

    @classmethod
    def create_category_type_tree_nodes(cls, queryset, pid, show_empty=True, show_count=True):
        counts = cls.get_tree_node_counts(queryset)
        tree_nodes = []

        # 类别的节点
        tree_nodes += cls.create_category_tree_nodes(
            pid, counts, show_empty=show_empty,
            show_count=show_count
        )

        # 类型的节点
        tree_nodes += cls.create_types_tree_nodes(
            pid, counts, show_empty=show_empty,
            show_count=show_count
        )
        return tree_nodes

    @classmethod
    def create_tree_nodes(cls, queryset, root_node=None, show_empty=True, show_count=True):
        tree_nodes = []

        # 根节点有可能是组织名称
        if root_node is None:
            root_node = cls.create_root_tree_node(queryset, show_count=show_count)
            tree_nodes.append(root_node)

        tree_nodes += cls.create_category_type_tree_nodes(
            queryset, root_node.id, show_empty=show_empty, show_count=show_count
        )

        # 应用的节点
        for app in queryset:
            if not settings.XPACK_ENABLED and const.AppType.is_xpack(app.type):
                continue
            node = app.as_tree_node(root_node.id)
            tree_nodes.append(node)
        return tree_nodes

    def create_app_tree_pid(self, root_id):
        pid = self.create_tree_id(root_id, 'category', self.category)
        pid = self.create_tree_id(pid, 'type', self.type)
        return pid

    def as_tree_node(self, pid, k8s_as_tree=False):
        from ..utils import KubernetesTree
        if self.type == const.AppType.k8s and k8s_as_tree:
            node = KubernetesTree(pid).as_tree_node(self)
        else:
            node = self._as_tree_node(pid)
        return node

    def _attrs_to_tree(self):
        if self.category == const.AppCategory.db:
            return self.attrs
        return {}

    def _as_tree_node(self, pid):
        icon_skin_category_mapper = {
            'remote_app': 'chrome',
            'db': 'database',
            'cloud': 'cloud'
        }
        icon_skin = icon_skin_category_mapper.get(self.category, 'file')
        pid = self.create_app_tree_pid(pid)
        node = TreeNode(**{
            'id': str(self.id),
            'name': self.name,
            'title': self.name,
            'pId': pid,
            'isParent': False,
            'open': False,
            'iconSkin': icon_skin,
            'meta': {
                'type': 'application',
                'data': {
                    'category': self.category,
                    'type': self.type,
                    'attrs': self._attrs_to_tree()
                }
            }
        })
        return node


class Application(CommonModelMixin, OrgModelMixin, ApplicationTreeNodeMixin):
    APP_TYPE = const.AppType

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    category = models.CharField(
        max_length=16, choices=const.AppCategory.choices, verbose_name=_('Category')
    )
    type = models.CharField(
        max_length=16, choices=const.AppType.choices, verbose_name=_('Type')
    )
    domain = models.ForeignKey(
        'assets.Domain', null=True, blank=True, related_name='applications',
        on_delete=models.SET_NULL, verbose_name=_("Domain"),
    )
    attrs = models.JSONField(default=dict, verbose_name=_('Attrs'))
    comment = models.TextField(
        max_length=128, default='', blank=True, verbose_name=_('Comment')
    )

    class Meta:
        verbose_name = _('Application')
        unique_together = [('org_id', 'name')]
        ordering = ('name',)
        permissions = [
            ('match_application', _('Can match application')),
        ]

    def __str__(self):
        category_display = self.get_category_display()
        type_display = self.get_type_display()
        return f'{self.name}({type_display})[{category_display}]'

    @property
    def category_remote_app(self):
        return self.category == const.AppCategory.remote_app.value

    @property
    def category_cloud(self):
        return self.category == const.AppCategory.cloud.value

    @property
    def category_db(self):
        return self.category == const.AppCategory.db.value

    def is_type(self, tp):
        return self.type == tp

    def get_rdp_remote_app_setting(self):
        from applications.serializers.attrs import get_serializer_class_by_application_type
        if not self.category_remote_app:
            raise ValueError(f"Not a remote app application: {self.name}")
        serializer_class = get_serializer_class_by_application_type(self.type)
        fields = serializer_class().get_fields()

        parameters = [self.type]
        for field_name in list(fields.keys()):
            if field_name in ['asset']:
                continue
            value = self.attrs.get(field_name)
            if not value:
                continue
            if field_name == 'path':
                value = '\"%s\"' % value
            parameters.append(str(value))

        parameters = ' '.join(parameters)
        return {
            'program': '||jmservisor',
            'working_directory': '',
            'parameters': parameters
        }

    def get_remote_app_asset(self, raise_exception=True):
        asset_id = self.attrs.get('asset')
        if is_uuid(asset_id):
            return Asset.objects.filter(id=asset_id).first()
        if raise_exception:
            raise ValueError("Remote App not has asset attr")

    def get_target_ip(self):
        target_ip = ''
        if self.category_remote_app:
            asset = self.get_remote_app_asset()
            target_ip = asset.ip if asset else target_ip
        elif self.category_cloud:
            target_ip = self.attrs.get('cluster')
        elif self.category_db:
            target_ip = self.attrs.get('host')
        return target_ip


class ApplicationUser(SystemUser):
    class Meta:
        proxy = True
        verbose_name = _('Application user')

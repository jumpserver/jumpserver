from django.db import models
from django.db.models import Count
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.models import OrgModelMixin
from common.mixins import CommonModelMixin
from common.tree import TreeNode
from assets.models import Asset, SystemUser
from .. import const


class ApplicationTreeNodeMixin:
    id: str
    name: str
    type: str
    category: str

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
    def create_category_tree_nodes(cls, root_node, counts=None, show_empty=True, show_count=True):
        nodes = []
        categories = const.AppType.category_types_mapper().keys()
        for category in categories:
            i = root_node.id + '_' + category.value
            node = cls.create_choice_node(
                category, i, pid=root_node.id, tp='category',
                counts=counts, opened=True, show_empty=show_empty,
                show_count=show_count
            )
            if not node:
                continue
            nodes.append(node)
        return nodes

    @classmethod
    def create_types_tree_nodes(cls, root_node, counts, show_empty=True, show_count=True):
        nodes = []
        type_category_mapper = const.AppType.type_category_mapper()
        for tp in const.AppType.type_category_mapper().keys():
            category = type_category_mapper.get(tp)
            pid = root_node.id + '_' + category.value
            i = root_node.id + '_' + tp.value
            node = cls.create_choice_node(
                tp, i, pid, tp='type', counts=counts,
                show_empty=show_empty, show_count=show_count
            )
            if not node:
                continue
            nodes.append(node)
        return nodes

    @staticmethod
    def get_tree_node_counts(queryset):
        counts = {'applications': queryset.count()}
        category_counts = queryset.annotate(count=Count('id'))\
            .values('category', 'count') \
            .order_by()
        for item in category_counts:
            counts[item['category']] = item['count']

        type_counts = queryset.annotate(count=Count('id')) \
            .values('type', 'count') \
            .order_by()
        for item in type_counts:
            counts[item['type']] = item['count']
        return counts

    @classmethod
    def create_tree_nodes(cls, queryset, root_node=None, show_empty=True, show_count=True):
        counts = cls.get_tree_node_counts(queryset)
        tree_nodes = []

        # 根节点有可能是组织名称
        if root_node is None:
            root_node = cls.create_root_tree_node(queryset, show_count=show_count)
            tree_nodes.append(root_node)

        # 类别的节点
        tree_nodes += cls.create_category_tree_nodes(
            root_node, counts, show_empty=show_empty,
            show_count=show_count
        )

        # 类型的节点
        tree_nodes += cls.create_types_tree_nodes(
            root_node, counts, show_empty=show_empty,
            show_count=show_count
        )

        # 应用的节点
        for app in queryset:
            pid = root_node.id + '_' + app.type
            tree_nodes.append(app.as_tree_node(pid))
        return tree_nodes

    def as_tree_node(self, pid):
        icon_skin_category_mapper = {
            'remote_app': 'chrome',
            'db': 'database',
            'cloud': 'cloud'
        }
        icon_skin = icon_skin_category_mapper.get(self.category, 'file')
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
                }
            }
        })
        return node


class Application(CommonModelMixin, OrgModelMixin, ApplicationTreeNodeMixin):
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
        unique_together = [('org_id', 'name')]
        ordering = ('name',)

    def __str__(self):
        category_display = self.get_category_display()
        type_display = self.get_type_display()
        return f'{self.name}({type_display})[{category_display}]'

    @property
    def category_remote_app(self):
        return self.category == const.AppCategory.remote_app.value

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

    def get_remote_app_asset(self):
        asset_id = self.attrs.get('asset')
        if not asset_id:
            raise ValueError("Remote App not has asset attr")
        asset = Asset.objects.filter(id=asset_id).first()
        return asset


class ApplicationUser(SystemUser):
    class Meta:
        proxy = True

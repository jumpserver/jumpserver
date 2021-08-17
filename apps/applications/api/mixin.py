from django.utils.translation import ugettext as _

from common.tree import TreeNode
from orgs.models import Organization
from ..models import Application

__all__ = ['SerializeApplicationToTreeNodeMixin']


class SerializeApplicationToTreeNodeMixin:
    @staticmethod
    def filter_organizations(applications):
        organization_ids = set(applications.values_list('org_id', flat=True))
        organizations = [Organization.get_instance(org_id) for org_id in organization_ids]
        organizations.sort(key=lambda x: x.name)
        return organizations

    @staticmethod
    def create_root_node():
        name = _('My applications')
        node = TreeNode(**{
            'id': 'applications',
            'name': name,
            'title': name,
            'pId': '',
            'open': True,
            'isParent': True,
            'meta': {
                'type': 'root'
            }
        })
        return node

    def serialize_applications_with_org(self, applications):
        root_node = self.create_root_node()
        tree_nodes = [root_node]
        organizations = self.filter_organizations(applications)

        for i, org in enumerate(organizations):
            # 组织节点
            org_node = org.as_tree_node(pid=root_node.id)
            tree_nodes.append(org_node)
            org_applications = applications.filter(org_id=org.id)
            count = org_applications.count()
            org_node.name += '({})'.format(count)

            # 各应用节点
            apps_nodes = Application.create_tree_nodes(
                queryset=org_applications, root_node=org_node,
                show_empty=False
            )
            tree_nodes += apps_nodes
        return tree_nodes

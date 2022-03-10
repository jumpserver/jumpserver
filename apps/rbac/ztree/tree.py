import random
from collections import defaultdict
from django.utils.translation import ugettext
from common.tree import TreeNode as RawTreeNode
from django.utils.translation import gettext_lazy as _, gettext
from rbac.models import Permission, ContentType
from django.db.models import F, Count
from .permissions import permission_paths, flag_license_required, flag_sep, flag_scope_system
from .tree_nodes import permission_tree_nodes
from ..const import Scope
from jumpserver.utils import has_valid_xpack_license


class TreeNode(RawTreeNode):
    total_count = 0
    checked_count = 0

    def checked_if_need(self):
        self.checked = self.total_count == self.checked_count

    def refresh_name(self):
        self.name = str(self.name) + f'({self.checked_count}/{self.total_count})'


class TreeNodes:

    def __init__(self):
        self.tree_nodes = defaultdict(TreeNode)

    def add_node(self, data):
        tree_node = self.add(data)
        tree_node.total_count += 1

    def add_leaf(self, data):
        tree_node = self.add(data)
        if not data['checked']:
            return

        parent_node = self.tree_nodes.get(tree_node.pId)
        while parent_node:
            parent_node.checked_count += 1
            parent_node = self.tree_nodes.get(parent_node.pId)

    def add(self, data):
        _id = data['id']
        data['name'] = data.get('name') or data['id']
        tree_node = self.tree_nodes.get(_id, TreeNode(**data))
        self.tree_nodes[tree_node.id] = tree_node
        return tree_node

    def get(self):
        tree_nodes = list(self.tree_nodes.values())
        for tree_node in tree_nodes:
            if not tree_node.isParent:
                continue
            tree_node.refresh_name()
            tree_node.checked_if_need()
        return tree_nodes


class ZTree(object):

    has_valid_license = has_valid_xpack_license()

    def __init__(self, checked_permission, scope, check_disabled=False):
        self.scope = scope
        self.checked_permission = self.prefetch_permissions(
            checked_permission
        )
        self.checked_permissions_mapper = {p.id: p for p in self.checked_permission}
        self.permissions = self.prefetch_permissions(
            Permission.get_permissions(scope)
        )
        self.permissions_mapper = {p.app_label_codename: p for p in self.permissions}
        self.content_types_name_mapper = {ct.model: ct.name for ct in ContentType.objects.all()}
        self.check_disabled = check_disabled
        self.tree_nodes = TreeNodes()
        self.show_node_level = 11

    @staticmethod
    def prefetch_permissions(permissions):
        return permissions.select_related('content_type') \
            .annotate(app=F('content_type__app_label')) \
            .annotate(model=F('content_type__model'))

    def get_tree_nodes(self):
        perm_paths = self.__class__.get_permission_paths(self.scope)
        for perm_path in perm_paths:
            self.generate_tree_nodes_by_path(perm_path)
        return self.tree_nodes.get()

    def generate_tree_nodes_by_path(self, perm_path):
        path, perm_app_label_codename = perm_path.rsplit('/', 1)

        # add path
        path_list = path.lstrip('/').split('/')
        pid = ''
        for level, tree_node_id in enumerate(path_list, start=1):
            name = _('Detail') if 'detail' in tree_node_id else tree_node_id
            data = dict({
                'id': tree_node_id,
                'name': name,
                'title': name,
                'pId': pid,
                'isParent': True,
                'chkDisabled': self.check_disabled,
                'open': level < self.show_node_level,
                'meta': {
                    'type': 'perm',
                }
            })
            _data = permission_tree_nodes.get(tree_node_id, {})
            data.update(_data)
            pid = data['id']
            self.tree_nodes.add_node(data)

        # add perm
        if not perm_app_label_codename:
            return
        perm = self.permissions_mapper.get(perm_app_label_codename)
        if perm:
            # 解决同一个权限不能在多个节点的问题
            _id = f'{pid}#{perm.id}'
            name = self._get_permission_name(perm)
            checked = perm.id in self.checked_permissions_mapper
        else:
            #  最终不应该走这里，所有权限都要在数据库里
            _id = perm_app_label_codename
            name = perm_app_label_codename
            checked = False

        data = {
            'id': _id,
            'pId': pid,
            'name': name,
            'title': perm_app_label_codename,
            'chkDisabled': self.check_disabled,
            'isParent': False,
            'iconSkin': 'file',
            'open': False,
            'checked': checked,
            'meta': {
                'type': 'perm',
            }
        }
        _data = permission_tree_nodes.get(perm_app_label_codename, {})
        data.update(_data)
        self.tree_nodes.add_leaf(data)

    def _get_permission_name(self, p):
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

        if ct in self.content_types_name_mapper:
            name += self.content_types_name_mapper[ct]
        else:
            name = gettext(p.name)
            name = name.replace('Can ', '').replace('可以', '')
        return name

    @classmethod
    def get_permissions_app_label_codename(cls, scope):
        perm_paths = cls.get_permission_paths(scope)
        perms = []
        for path in perm_paths:
            path, app_label_code_name = path.rsplit('/', 1)
            if not app_label_code_name:
                continue
            perms.append(app_label_code_name)
        return perms

    @classmethod
    def get_permission_paths(cls, scope):
        perm_paths = []
        for path in permission_paths:
            if flag_sep in path:
                path, flags = path.split(flag_sep)
                if flag_scope_system in flags and scope == Scope.org:
                    continue
                if flag_license_required in flags and not cls.has_valid_license:
                    continue
            perm_paths.append(path)
        return perm_paths

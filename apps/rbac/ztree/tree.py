from collections import defaultdict
from django.utils.translation import ugettext
from common.tree import TreeNode
from django.utils.translation import gettext_lazy as _, gettext
from rbac.models import Permission, ContentType
from django.db.models import F, Count
from .permissions import permission_paths
from .tree_nodes import permission_tree_nodes


class TreeNodes:

    def __init__(self):
        self.tree_nodes = defaultdict(TreeNode)

    def add(self, data):
        _id = data['id']
        name = data.get('name', _id)
        data['name'] = name
        tree_node = TreeNode(**data)
        self.tree_nodes[tree_node.id] = tree_node

    def get(self):
        return list(self.tree_nodes.values())


class ZTree(object):

    def __init__(self, scop):
        self.scop = scop
        self.permissions = self.prefetch_permissions()
        self.permissions_mapper = {p.app_label_codename: p for p in self.permissions}
        self.tree_nodes = TreeNodes()
        content_types = ContentType.objects.all()
        self.content_types_name_mapper = {ct.model: ct.name for ct in content_types}

    @staticmethod
    def prefetch_permissions():
        return Permission.objects.all().select_related('content_type') \
            .annotate(app=F('content_type__app_label')) \
            .annotate(model=F('content_type__model'))

    def get_tree_nodes(self):
        self.create_tree_nodes()
        return self.tree_nodes.get()

    def create_tree_nodes(self):
        perm_paths = self.get_permission_paths()
        for perm_path in perm_paths:
            self.create_tree_nodes_by_path(perm_path)

    def create_tree_nodes_by_path(self, perm_path):
        path, perm_app_label_codename = perm_path.rsplit('/', 1)
        # add path
        pid = ''
        for level, tree_node_id in enumerate(path.lstrip('/').split('/'), start=1):
            if 'detail' in tree_node_id:
                name = _('Detail')
            else:
                name = tree_node_id

            data = {
                'id': tree_node_id,
                'pId': pid,
                'name': name
            }
            if level <= 1 or True:
                data.update({
                    'open': True
                })
            _data = permission_tree_nodes.get(tree_node_id, {})
            data.update(_data)
            pid = data['id']
            self.tree_nodes.add(data)

        # add perm
        if not perm_app_label_codename:
            return
        perm = self.permissions_mapper.get(perm_app_label_codename)
        if perm:
            _id = f'{pid}#{perm.id}',
            name = self._get_permission_name(perm)
        else:
            _id = perm_app_label_codename
            name = perm_app_label_codename

        data = {
            'id': _id,
            'pId': pid,
            'name': name,
            'isParent': False,
            'iconSkin': 'file',
            'open': False,
        }
        _data = permission_tree_nodes.get(perm_app_label_codename, {})
        data.update(_data)
        self.tree_nodes.add(data)

    def get_permission_paths(self):
        # filter scop
        # filter license
        print(self.scop)
        perm_paths = []
        for path in permission_paths:
            # if '.' not in path:
            #     continue
            if '@' in path:
                path, flags = path.split('@')
            # if flags
            perm_paths.append(path)
        return perm_paths

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

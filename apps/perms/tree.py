# coding: utf-8
#


from django.db.models import Q
from perms.models import AssetPermission
from collections import defaultdict


class DuplicatedNodeIdError(Exception):
    """Exception throwed if an identifier already exists in a tree."""
    pass


class MultipleRootError(Exception):
    """Exception throwed if more than one root exists in a tree."""
    pass


class NodePropertyError(Exception):
    """Basic Node attribute error"""
    pass


class NodeIDAbsentError(NodePropertyError):
    """Exception throwed if a node's identifier is unknown"""
    pass


class AssetPermissionTree(object):

    def __init__(self, permissions):
        super().__init__()
        # QuerySet AssetPermission object
        self.__permissions = permissions
        # dictionary, identifier: AssetPermissionNode object
        self._nodes = {}
        # identifier of the root node
        self.root = None

        # {"asset_instance": set("system_user",)}
        self.__assets = defaultdict(set)
        # {"node_identifier": "AssetPermissionNode"}
        self.__nodes = {}

        self.__init_tree()

    def __setitem__(self, key, value):
        """Set _nodes[key]"""
        self._nodes.update({key: value})

    def __getitem__(self, key):
        """Return _nodes[key]"""
        try:
            return self._nodes[key]
        except KeyError:
            raise NodeIDAbsentError('Node {} is not in the tree'.format(key))

    def __len__(self):
        return len(self._nodes)

    @property
    def permissions(self):
        return self.__permissions

    def update_assets(self, asset, system_users):
        self.__assets[asset].update(system_users)

    def __init_tree(self):
        # self.__init_permissions()
        self.__init_assets()
        self.__init_nodes()
        self.__sorted_nodes()
        self.__construct_tree()

    def __init_assets(self):
        permissions = self.permissions.prefetch_related('assets', 'nodes', 'system_users')
        for perm in permissions:
            for asset in perm.assets.all():
                self.update_assets(asset, list(perm.system_users.all()))

            for node in perm.nodes.all():
                for asset in node.get_all_assets():
                    self.update_assets(asset, list(perm.system_users.all()))

    def __init_nodes(self):

        for asset, system_users in self.__assets.items():

            # Tree -> Node[asset<asset.system_users>]
            asset.system_users = system_users

            for node_direct in asset.nodes.all():
                nodes = [node for node in node_direct.get_ancestor()]
                nodes.append(node_direct)

                for node in nodes:

                    if node.key in self.__nodes.keys():
                        self.__nodes[node.key].add_asset(asset)
                        continue

                    _node = AssetPermissionNode(node)
                    _node.add_asset(asset)
                    self.__nodes.update({node.key: _node})

    def __sorted_nodes(self):
        self.__nodes = dict(sorted(self.__nodes.items(), key=lambda item: item[0]))

    def __construct_tree(self):
        for nid, node in self.__nodes.items():
            parent = self.__nodes.get(node.identifier[:node.identifier.rfind(':')], None)
            self.add_nodes(node, parent=parent)

    def contains(self, nid):
        """Check if the tree contains node of given id"""
        return True if nid in self._nodes else False

    def nodes(self):
        for node in self.all_nodes():
            print('=========')
            print('nid: ', node.identifier)
            print('Pid: ', node.bpointer)
            print('assets: ', node.assets)
            for asset in node.assets:
                print('{} system_users: {}'.format(asset, asset.system_users))

    def all_nodes(self):
        """Return all nodes in a list"""
        return list(self._nodes.values())

    def add_nodes(self, node, parent=None):
        """
        Add a new node to tree
        """
        if not isinstance(node, AssetPermissionNode):
            raise OSError("First parameter must be object of Class::Node")

        if node.identifier in self._nodes:
            raise DuplicatedNodeIdError(
                "Can't create node with ID {}".format(node.identifier)
            )

        pid = parent.identifier if isinstance(parent, AssetPermissionNode) else parent

        if pid is None:
            if self.root is not None:
                raise MultipleRootError("A tree takes one root merely.")
            else:
                self.root = node.identifier
        elif not self.contains(pid):
            raise NodeIDAbsentError("Parent node {} is not in the tree".format(pid))

        self._nodes.update({node.identifier: node})
        self.__update_fpointer(pid, node.identifier, AssetPermissionNode.ADD)
        self.__update_bpointer(node.identifier, pid)

    def __update_fpointer(self, nid, child_id, mode):
        if nid is None:
            return
        else:
            self[nid].update_fpointer(child_id, mode)

    def __update_bpointer(self, nid, parent_id):
        self[nid].update_bpointer(parent_id)

    def is_branch(self, nid):
        if nid is None:
            raise OSError("First parameter can't be None")

        if not self.contains(nid):
            raise NodeIDAbsentError("Node {} is not in the tree".format(nid))

        try:
            fpointer = self[nid].fpointer
        except KeyError:
            fpointer = []
        return fpointer

    def children(self, nid):
        """
        Return the children (Node) list of nid.
        Empty list is returned if nid does not exist
        """
        return [self[i] for i in self.is_branch(nid)]

    def descendant(self, nid):
        """
        Return the descendant(子孙) (Node) list of nid.
        Empty list is returned if nid does not exist
        """
        pass

    def parent(self, nid):
        if not self.contains(nid):
            raise NodeIDAbsentError('Node {} is not in the tree'.format(nid))

        pid = self[nid].bpointer
        if pid is None or not self.contains(pid):
            return None

        return self[pid]

    def to_dict(self, nid=None):
        nid = self.root if (nid is None) else nid
        ntag = self[nid].tag
        assets = [str(asset) for asset in self[nid].assets]

        tree_dict = {ntag: {"children": []}}
        tree_dict[ntag]['assets'] = assets
        queue = [self[i] for i in self[nid].fpointer]
        for elem in queue:
            tree_dict[ntag]["children"].append(self.to_dict(elem.identifier))

        if len(tree_dict[ntag]["children"]) == 0:
            tree_dict = {ntag: {"assets": assets}}

        return tree_dict


class AssetPermissionNode(object):

    (ADD, DELETE, INSERT, REPLACE) = list(range(4))

    def __init__(self, node, asset=None):
        """
        :param node: assets.models.node.Node
        :param asset: assets.models.asset.Asset
        """
        self._identifier = node.key
        self._node = node
        # identifier of the parent's node
        self._bpointer = None
        # identifier(s) of the soons' nodes(s)
        self._fpointer = list()

        self.tag = node.name
        self._assets = set()
        if asset is not None:
            self.add_asset(asset)

    def __str__(self):
        return self.tag

    @property
    def assets(self):
        return list(self._assets)
        # return [str(assets) for assets in self._assets]

    @property
    def identifier(self):
        return self._identifier

    @property
    def bpointer(self):
        return self._bpointer

    @bpointer.setter
    def bpointer(self, nid):
        self._bpointer = nid

    def update_bpointer(self, nid):
        self.bpointer = nid

    @property
    def fpointer(self):
        return self._fpointer

    @fpointer.setter
    def fpointer(self, value):
        if value is None:
            self._fpointer = list()
        elif isinstance(value, list):
            self._fpointer = value
        elif isinstance(value, dict):
            self._fpointer = list(value.keys())
        elif isinstance(value, set):
            self._fpointer = list(value)
        else:
            pass

    def update_fpointer(self, nid, mode=ADD, replace=None):
        if nid is None:
            return

        if mode is self.ADD:
            self._fpointer.append(nid)

        elif mode is self.DELETE:
            if nid in self._fpointer:
                self._fpointer.remove(nid)

        elif mode is self.INSERT:
            self.update_fpointer(nid)

        elif mode is self.REPLACE:
            if replace is None:
                pass
            ind = self._fpointer.index(nid)
            self._fpointer[ind] = replace

    def is_leaf(self):
        if len(self.fpointer) == 0:
            return True
        else:
            return False

    def is_root(self):
        return self._bpointer is None

    def add_asset(self, asset):
        self._assets.add(asset)

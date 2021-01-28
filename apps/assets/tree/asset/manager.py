from common.decorator import singleton
from .tree import AssetTree


__all__ = ['AssetTreeManager']


@singleton
class AssetTreeManager(object):
    """ 资产树管理器 """

    def __init__(self):
        self._org_tree_mapping = {}

    def get_tree(self, org_id):
        _tree = self.__get_tree(org_id=org_id)
        if _tree is None:
            _tree = self.__initial_tree(org_id)
            self.__set_tree(org_id, _tree)
        return _tree

    def refresh_tree(self, org_id):
        self.destroy_tree(org_id)
        _tree = self.__initial_tree(org_id)
        self.__set_tree(_tree, org_id)
        return _tree

    def destroy_tree(self, org_id):
        return self._org_tree_mapping.pop(org_id, None)

    def __set_tree(self, org_id, tree):
        self._org_tree_mapping[org_id] = tree

    def __get_tree(self, org_id):
        return self._org_tree_mapping.get(org_id)

    @staticmethod
    def __initial_tree(org_id):
        _tree = AssetTree(org_id=org_id)
        _tree.initial()
        return _tree


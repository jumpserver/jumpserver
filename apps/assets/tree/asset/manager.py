from django.db.models import TextChoices
from common.decorator import singleton
from .tree import AssetTree
from assets.signals import org_asset_tree_change


__all__ = ['AssetTreeManager']


@singleton
class AssetTreeManager(object):
    """ 资产树管理器 """

    class ActionChoices(TextChoices):
        refresh = 'refresh', 'Refresh tree'
        destroy = 'destroy', 'Destroy tree'

    def __init__(self):
        self._org_tree_mapping = {}

    def get_tree(self, org_id):
        _tree = self.__get_tree(org_id=org_id)
        if _tree is None:
            _tree = self.refresh_tree(org_id=org_id)
        return _tree

    def refresh_tree(self, org_id):
        return self.__refresh_tree(org_id=org_id)

    def __refresh_tree(self, org_id):
        self.__destroy_tree(org_id)
        _tree = self.__initial_tree(org_id)
        self.__set_tree(_tree, org_id)
        org_asset_tree_change.send(action=self.ActionChoices.refresh, org_id=org_id)
        return _tree

    def __set_tree(self, org_id, tree):
        self._org_tree_mapping[org_id] = tree

    def __get_tree(self, org_id):
        return self._org_tree_mapping.get(org_id)

    @staticmethod
    def __initial_tree(org_id):
        _tree = AssetTree(org_id=org_id)
        _tree.initial()
        return _tree

    def __destroy_tree(self, org_id):
        return self._org_tree_mapping.pop(org_id, None)

    def processor_tree(self, action, org_id):
        method_name = '__{}_tree'.format(action)
        method = getattr(self, method_name, None)
        if callable(method):
            return method(org_id=org_id)


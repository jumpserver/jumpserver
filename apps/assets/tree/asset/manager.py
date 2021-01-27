from django.dispatch import receiver
from common.signals import django_ready
from .tree import AssetTree


def singleton(cls):
    _instance = {}

    def _singleton(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return _singleton


@singleton
class AssetTreeManager(object):
    """ 资产树管理器 """

    def __init__(self):
        self._org_tree_mapping = {}

    def get_tree(self, org_id):
        _tree = self.__get_tree(org_id=org_id)
        if _tree is None:
            _tree = self.__create_tree(org_id=org_id)
            self.__set_tree(org_id=org_id, tree=_tree)
        return _tree

    def __set_tree(self, org_id, tree):
        self._org_tree_mapping[org_id] = tree

    def __get_tree(self, org_id):
        return self._org_tree_mapping.get(org_id)

    @staticmethod
    def __create_tree(org_id):
        _tree = AssetTree(org_id=org_id)
        _tree.initial()
        return _tree

    def __destroy_tree(self, org_id):
        return self._org_tree_mapping.pop(org_id, None)


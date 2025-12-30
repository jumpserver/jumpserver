from django.db.models import TextChoices


__all__ = [
    'RenderTreeType', 'RenderTreeTypeChoices',
    'RenderTreeView', 'RenderTreeViewChoices',
]


class RenderTreeViewChoices(TextChoices):
    node = 'node', 'Node View'
    category = 'category', 'Category View'


class RenderTreeView:
    
    def __init__(self, view):
        if view not in RenderTreeViewChoices.values:
            raise ValueError(f'Invalid tree view: {view}')
        self.view: RenderTreeViewChoices = view

    @property
    def is_node_view(self):
        return self.view == RenderTreeViewChoices.node

    @property
    def is_category_view(self):
        return self.view == RenderTreeViewChoices.category

    def __str__(self):
        return self.view.value


class RenderTreeTypeChoices(TextChoices):
    node = 'node', 'Node'
    asset = 'asset', 'Asset'


class RenderTreeType:

    def __init__(self, _type):
        if _type not in RenderTreeTypeChoices.values:
            raise ValueError(f'Invalid tree type: {_type}')
        self._type: RenderTreeTypeChoices = _type

    @property
    def is_asset_tree(self):
        return self._type == RenderTreeTypeChoices.asset

    @property
    def is_node_tree(self):
        return self._type == RenderTreeTypeChoices.node
    
    def __str__(self):
        return self._type.value

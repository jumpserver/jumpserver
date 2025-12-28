from django.db.models import TextChoices


__all__ = ['RenderTreeType', 'RenderTreeTypeChoices']


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

from django.db.models import TextChoices


__all__ = [
    'RenderTreeView', 'RenderTreeViewChoices',
]


class RenderTreeViewChoices(TextChoices):
    node = 'node', 'Node tree'
    category = 'category', 'Category tree'


class RenderTreeView:
    
    def __init__(self, view):
        if view not in RenderTreeViewChoices.values:
            view = RenderTreeViewChoices.node
        self.view: RenderTreeViewChoices = view

    @property
    def is_node_view(self):
        return self.view == RenderTreeViewChoices.node

    @property
    def is_category_view(self):
        return self.view == RenderTreeViewChoices.category

    def __str__(self):
        return self.view.value

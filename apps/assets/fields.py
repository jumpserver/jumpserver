from django.utils.functional import cached_property
from django.db.models.fields.related_descriptors import (
    ManyToManyDescriptor, create_forward_many_to_many_manager
)


def take_in_no_node_assets():
    from assets.models import Asset, Node
    assets = Asset.objects.filter(nodes__isnull=True).distinct().values_list('id', flat=True)
    Node.org_root().assets.add(*assets)


def create_asset_node_forward_many_to_many_manager(superclass, rel, reverse):
    Manager = create_forward_many_to_many_manager(superclass, rel, reverse)

    class AssetNodeManyRelatedManager(Manager):
        def clear(self):
            ret = super().clear()
            if not getattr(self, '_doing_set', False):
                take_in_no_node_assets()
            return ret
        clear.alters_data = True

        def set(self, objs, *, clear=False, through_defaults=None):
            self._doing_set = True
            ret = super().set(objs, clear=clear, through_defaults=through_defaults)
            self._doing_set = False
            take_in_no_node_assets()
            return ret
        set.alters_data = True

        def remove(self, *objs):
            ret = super().remove(*objs)
            if not getattr(self, '_doing_set', False):
                take_in_no_node_assets()
            return ret
        remove.alters_data = True
    return AssetNodeManyRelatedManager


class AssetNodeManyToManyDescriptor(ManyToManyDescriptor):
    @cached_property
    def related_manager_cls(self):
        related_model = self.rel.related_model if self.reverse else self.rel.model

        return create_asset_node_forward_many_to_many_manager(
            related_model._default_manager.__class__,
            self.rel,
            reverse=self.reverse,
        )

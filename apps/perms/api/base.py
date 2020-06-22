from django.db.models import F
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins.api import OrgRelationMixin


__all__ = [
    'RelationViewSet'
]


class RelationViewSet(OrgRelationMixin, OrgBulkModelViewSet):
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(**{f'{self.from_field}_display': F(f'{self.from_field}__name')})
        return queryset

from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_bulk import BulkModelViewSet

from .mixin import CommonApiMixin, RelationMixin
from .permission import AllowBulkDestroyMixin


class JMSGenericViewSet(CommonApiMixin, GenericViewSet):
    pass


class JMSModelViewSet(CommonApiMixin, ModelViewSet):
    pass


class JMSBulkModelViewSet(CommonApiMixin, AllowBulkDestroyMixin, BulkModelViewSet):
    pass


class JMSBulkRelationModelViewSet(CommonApiMixin, RelationMixin, AllowBulkDestroyMixin, BulkModelViewSet):
    pass

from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet, ViewSet
from rest_framework_bulk import BulkModelViewSet

from ..mixins.api import (
    RelationMixin, AllowBulkDestroyMixin, CommonApiMixin
)


class JMSGenericViewSet(CommonApiMixin, GenericViewSet):
    pass


class JMSViewSet(CommonApiMixin, ViewSet):
    pass


class JMSModelViewSet(CommonApiMixin, ModelViewSet):
    pass


class JMSReadOnlyModelViewSet(CommonApiMixin, ReadOnlyModelViewSet):
    pass


class JMSBulkModelViewSet(CommonApiMixin, AllowBulkDestroyMixin, BulkModelViewSet):
    pass


class JMSBulkRelationModelViewSet(CommonApiMixin,
                                  RelationMixin,
                                  AllowBulkDestroyMixin,
                                  BulkModelViewSet):
    pass

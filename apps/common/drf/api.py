from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet, ViewSet
from rest_framework_bulk import BulkModelViewSet

from ..mixins.api import (
    RelationMixin, AllowBulkDestroyMixin, CommonMixin
)


class JMSGenericViewSet(CommonMixin, GenericViewSet):
    pass


class JMSViewSet(CommonMixin, ViewSet):
    pass


class JMSModelViewSet(CommonMixin, ModelViewSet):
    pass


class JMSReadOnlyModelViewSet(CommonMixin, ReadOnlyModelViewSet):
    pass


class JMSBulkModelViewSet(CommonMixin, AllowBulkDestroyMixin, BulkModelViewSet):
    pass


class JMSBulkRelationModelViewSet(CommonMixin,
                                  RelationMixin,
                                  AllowBulkDestroyMixin,
                                  BulkModelViewSet):
    pass

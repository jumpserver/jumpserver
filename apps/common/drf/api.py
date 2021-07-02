from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_bulk import BulkModelViewSet

from ..mixins.api import (
    SerializerMixin, QuerySetMixin, ExtraFilterFieldsMixin, PaginatedResponseMixin,
    RelationMixin, AllowBulkDestroyMixin, RenderToJsonMixin,
)


class CommonMixin(SerializerMixin,
                  QuerySetMixin,
                  ExtraFilterFieldsMixin,
                  PaginatedResponseMixin,
                  RenderToJsonMixin):
    pass


class JmsGenericViewSet(CommonMixin,
                        GenericViewSet):
    pass


class JMSModelViewSet(CommonMixin,
                      ModelViewSet):
    pass


class JMSBulkModelViewSet(CommonMixin,
                          AllowBulkDestroyMixin,
                          BulkModelViewSet):
    pass


class JMSBulkRelationModelViewSet(CommonMixin,
                                  RelationMixin,
                                  AllowBulkDestroyMixin,
                                  BulkModelViewSet):
    pass

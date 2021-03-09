from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_bulk import BulkModelViewSet

from ..mixins.api import (
    SerializerMixin2, QuerySetMixin, ExtraFilterFieldsMixin, PaginatedResponseMixin,
    RelationMixin, AllowBulkDestoryMixin, ParseToJsonMixin,
)


class CommonMixin(SerializerMixin2,
                  QuerySetMixin,
                  ExtraFilterFieldsMixin,
                  PaginatedResponseMixin,
                  ParseToJsonMixin):
    pass


class JmsGenericViewSet(CommonMixin,
                        GenericViewSet):
    pass


class JMSModelViewSet(CommonMixin,
                      ModelViewSet):
    pass


class JMSBulkModelViewSet(CommonMixin,
                          AllowBulkDestoryMixin,
                          BulkModelViewSet):
    pass


class JMSBulkRelationModelViewSet(CommonMixin,
                                  RelationMixin,
                                  AllowBulkDestoryMixin,
                                  BulkModelViewSet):
    pass

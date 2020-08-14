from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_bulk import BulkModelViewSet

from ..mixins.api import (
    SerializerMixin2, QuerySetMixin, ExtraFilterFieldsMixin, PaginatedResponseMixin,
    RelationMixin, AllowBulkDestoryMixin
)


class JmsGenericViewSet(SerializerMixin2,
                        QuerySetMixin,
                        ExtraFilterFieldsMixin,
                        PaginatedResponseMixin,
                        GenericViewSet):
    pass


class JMSModelViewSet(SerializerMixin2,
                      QuerySetMixin,
                      ExtraFilterFieldsMixin,
                      PaginatedResponseMixin,
                      ModelViewSet):
    pass


class JMSBulkModelViewSet(SerializerMixin2,
                          QuerySetMixin,
                          ExtraFilterFieldsMixin,
                          PaginatedResponseMixin,
                          AllowBulkDestoryMixin,
                          BulkModelViewSet):
    pass


class JMSBulkRelationModelViewSet(SerializerMixin2,
                                  QuerySetMixin,
                                  ExtraFilterFieldsMixin,
                                  PaginatedResponseMixin,
                                  RelationMixin,
                                  AllowBulkDestoryMixin,
                                  BulkModelViewSet):
    pass

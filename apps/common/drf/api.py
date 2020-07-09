from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..mixins.api import (
    SerializerMixin2, QuerySetMixin, ExtraFilterFieldsMixin, PaginatedResponseMixin
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

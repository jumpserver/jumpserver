from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..mixins.api import SerializerMixin2, QuerySetMixin, ExtraFilterFieldsMixin


class JmsGenericViewSet(SerializerMixin2, QuerySetMixin, ExtraFilterFieldsMixin, GenericViewSet):
    pass


class JMSModelViewSet(SerializerMixin2, QuerySetMixin, ExtraFilterFieldsMixin, ModelViewSet):
    pass

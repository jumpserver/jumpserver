from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import (
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, DestroyModelMixin
)
from common.permissions import IsSuperUser
from ..models import AccountType
from .. import serializers


__all__ = ['AccountTypeViewSet']


class AccountTypeViewSet(CreateModelMixin, RetrieveModelMixin, ListModelMixin, DestroyModelMixin,
                         GenericViewSet):
    permission_classes = (IsSuperUser,)
    filterset_fields = ('name', 'protocol', 'category', 'secret_type', 'is_builtin', )
    search_fields = filterset_fields
    queryset = AccountType.objects.all()
    serializer_class = serializers.AccountTypeSerializer

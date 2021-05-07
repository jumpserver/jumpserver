from rest_framework.response import Response
from rest_framework.decorators import action
from orgs.mixins.api import OrgBulkModelViewSet
from .. import serializers
from ..models import Account
from .mixins import SafeViewSetMixin


__all__ = ['AccountViewSet']


class AccountViewSet(SafeViewSetMixin, OrgBulkModelViewSet):
    model = Account
    filterset_fields = {
        'id': ['exact', 'in'],
        'name': ['exact'],
        'username': ['exact'],
        'type': ['exact', 'in'],
        'type__name': ['exact', 'in'],
        'address': ['exact'],
        'is_privileged': ['exact'],
        'safe': ['exact', 'in'],
        'safe__name': ['exact']
    }
    search_fields = (
        'id', 'name', 'username', 'type__name', 'address', 'is_privileged', 'safe__name'
    )
    serializer_classes = {
        'default': serializers.AccountSerializer,
        'view_secret': serializers.AccountSecretSerializer,
    }
    extra_action_permission_mapping = {
        'view_secret': 'view_account_secret'
    }

    @action(methods=['get'], detail=True, url_path='secret')
    def view_secret(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(obj)
        return Response(serializer.data)

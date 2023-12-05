from typing import Callable

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.request import Request

from common.api import JMSModelViewSet
from common.permissions import IsServiceAccount
from common.utils import is_uuid
from rbac.permissions import RBACPermission
from terminal.models import AppProvider
from terminal.serializers import (
    VirtualAppPublicationSerializer
)


class ProviderMixin:
    request: Request
    permission_denied: Callable
    kwargs: dict
    rbac_perms = (
        ('list', 'terminal.view_appprovider'),
        ('retrieve', 'terminal.view_appprovider'),
    )

    def get_permissions(self):
        if self.kwargs.get('host') and settings.DEBUG:
            return [RBACPermission()]
        else:
            return [IsServiceAccount()]

    def self_provider(self):
        try:
            return self.request.user.terminal.app_provider
        except AttributeError:
            raise self.permission_denied(self.request, 'User has no app provider')

    def pk_provider(self):
        return get_object_or_404(AppProvider, id=self.kwargs.get('provider'))

    @property
    def provider(self):
        if self.kwargs.get('provider'):
            host = self.pk_provider()
        else:
            host = self.self_provider()
        return host


class AppProviderAppViewSet(ProviderMixin, JMSModelViewSet):
    provider: AppProvider
    serializer_class = VirtualAppPublicationSerializer
    filterset_fields = ['provider__name', 'app__name', 'status']

    def get_object(self):
        pk = self.kwargs.get('pk')
        if not is_uuid(pk):
            return self.provider.publications.get(app__name=pk)
        else:
            return self.provider.publications.get(id=pk)

    def get_queryset(self):
        queryset = self.provider.publications.all()
        return queryset

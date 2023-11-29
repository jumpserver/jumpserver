from typing import Callable

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.request import Request

from common.api import JMSModelViewSet
from common.permissions import IsServiceAccount
from common.utils import is_uuid
from rbac.permissions import RBACPermission
from terminal.models import VirtualHost
from terminal.serializers import (
    VirtualAppPublicationSerializer
)


class HostMixin:
    request: Request
    permission_denied: Callable
    kwargs: dict
    rbac_perms = (
        ('list', 'terminal.view_virtualhost'),
        ('retrieve', 'terminal.view_virtualhost'),
    )

    def get_permissions(self):
        if self.kwargs.get('host') and settings.DEBUG:
            return [RBACPermission()]
        else:
            return [IsServiceAccount()]

    def self_host(self):
        try:
            return self.request.user.terminal.virtual_host
        except AttributeError:
            raise self.permission_denied(self.request, 'User has no virtual host')

    def pk_host(self):
        return get_object_or_404(VirtualHost, id=self.kwargs.get('host'))

    @property
    def host(self):
        if self.kwargs.get('host'):
            host = self.pk_host()
        else:
            host = self.self_host()
        return host


class VirtualHostAppViewSet(HostMixin, JMSModelViewSet):
    host: VirtualHost
    serializer_class = VirtualAppPublicationSerializer
    filterset_fields = ['vhost__name', 'app__name', 'status']

    def get_object(self):
        pk = self.kwargs.get('pk')
        if not is_uuid(pk):
            return self.host.publications.get(app__name=pk)
        else:
            return self.host.publications.get(id=pk)

    def get_queryset(self):
        queryset = self.host.publications.all()
        return queryset

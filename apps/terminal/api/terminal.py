# -*- coding: utf-8 -*-
#
import logging
import uuid

from django.core.cache import cache
from rest_framework import generics
from rest_framework.views import APIView, Response
from rest_framework import status
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from common.exceptions import JMSException
from common.drf.api import JMSBulkModelViewSet
from common.utils import get_object_or_none
from common.permissions import IsAppUser, IsSuperUser, WithBootstrapToken
from ..models import Terminal
from .. import serializers
from .. import exceptions

__all__ = [
    'TerminalViewSet',  'TerminalConfig',
    'TerminalRegistrationApi',
]
logger = logging.getLogger(__file__)


class TerminalViewSet(JMSBulkModelViewSet):
    queryset = Terminal.objects.filter(is_deleted=False)
    serializer_class = serializers.TerminalSerializer
    permission_classes = (IsSuperUser,)
    filterset_fields = ['name', 'remote_addr', 'type']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.get_online_session_count() > 0:
            raise JMSException(
                code='have_online_session',
                detail=_('Have online sessions')
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list):
            raise exceptions.BulkCreateNotSupport()

        name = request.data.get('name')
        remote_ip = request.META.get('REMOTE_ADDR')
        x_real_ip = request.META.get('X-Real-IP')
        remote_addr = x_real_ip or remote_ip

        terminal = get_object_or_none(Terminal, name=name, is_deleted=False)
        if terminal:
            msg = 'Terminal name %s already used' % name
            return Response({'msg': msg}, status=409)

        serializer = self.serializer_class(data={
            'name': name, 'remote_addr': remote_addr
        })

        if serializer.is_valid():
            terminal = serializer.save()

            # App should use id, token get access key, if accepted
            token = uuid.uuid4().hex
            cache.set(token, str(terminal.id), 3600)
            data = {"id": str(terminal.id), "token": token, "msg": "Need accept"}
            return Response(data, status=201)
        else:
            data = serializer.errors
            logger.error("Register terminal error: {}".format(data))
            return Response(data, status=400)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        status = self.request.query_params.get('status')
        if not status:
            return queryset
        filtered_queryset_id = [str(q.id) for q in queryset if q.status == status]
        queryset = queryset.filter(id__in=filtered_queryset_id)
        return queryset


class TerminalConfig(APIView):
    permission_classes = (IsAppUser,)

    def get(self, request):
        config = request.user.terminal.config
        return Response(config, status=200)


class TerminalRegistrationApi(generics.CreateAPIView):
    serializer_class = serializers.TerminalRegistrationSerializer
    permission_classes = [WithBootstrapToken]
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        if not settings.SECURITY_SERVICE_ACCOUNT_REGISTRATION:
            data = {"error": "service account registration disabled"}
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

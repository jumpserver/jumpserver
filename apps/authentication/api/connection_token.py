# -*- coding: utf-8 -*-
#
import uuid

from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView

from common.utils import get_logger
from common.permissions import IsSuperUserOrAppUser
from orgs.mixins.api import RootOrgViewMixin

from ..serializers import ConnectionTokenSerializer

logger = get_logger(__name__)
__all__ = ['UserConnectionTokenApi']


class UserConnectionTokenApi(RootOrgViewMixin, CreateAPIView):
    permission_classes = (IsSuperUserOrAppUser,)
    serializer_class = ConnectionTokenSerializer

    def perform_create(self, serializer):
        user = serializer.validated_data['user']
        asset = serializer.validated_data['asset']
        system_user = serializer.validated_data['system_user']
        token = str(uuid.uuid4())
        value = {
            'user': str(user.id),
            'username': user.username,
            'asset': str(asset.id),
            'hostname': asset.hostname,
            'system_user': str(system_user.id),
            'system_user_name': system_user.name
        }
        cache.set(token, value, timeout=20)
        return token

    def create(self, request, *args, **kwargs):
        if not settings.CONNECTION_TOKEN_ENABLED:
            data = {'error': 'Connection token disabled'}
            return Response(data, status=400)

        if not request.user.is_superuser:
            data = {'error': 'Only super user can create token'}
            return Response(data, status=403)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = self.perform_create(serializer)
        return Response({"token": token}, status=201)

    def get(self, request):
        token = request.query_params.get('token')
        value = cache.get(token, None)

        if not value:
            return Response('', status=404)
        return Response(value)

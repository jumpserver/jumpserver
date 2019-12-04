# -*- coding: utf-8 -*-
#
import uuid

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import get_logger
from common.permissions import IsOrgAdminOrAppUser
from orgs.mixins.api import RootOrgViewMixin
from users.models import User
from assets.models import Asset, SystemUser

logger = get_logger(__name__)
__all__ = [
    'UserConnectionTokenApi',
]


class UserConnectionTokenApi(RootOrgViewMixin, APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def post(self, request):
        user_id = request.data.get('user', '')
        asset_id = request.data.get('asset', '')
        system_user_id = request.data.get('system_user', '')
        token = str(uuid.uuid4())
        user = get_object_or_404(User, id=user_id)
        asset = get_object_or_404(Asset, id=asset_id)
        system_user = get_object_or_404(SystemUser, id=system_user_id)
        value = {
            'user': user_id,
            'username': user.username,
            'asset': asset_id,
            'hostname': asset.hostname,
            'system_user': system_user_id,
            'system_user_name': system_user.name
        }
        cache.set(token, value, timeout=20)
        return Response({"token": token}, status=201)

    def get(self, request):
        token = request.query_params.get('token')
        user_only = request.query_params.get('user-only', None)
        value = cache.get(token, None)

        if not value:
            return Response('', status=404)

        if not user_only:
            return Response(value)
        else:
            return Response({'user': value['user']})

    def get_permissions(self):
        if self.request.query_params.get('user-only', None):
            self.permission_classes = (AllowAny,)
        return super().get_permissions()





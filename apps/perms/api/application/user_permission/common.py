# -*- coding: utf-8 -*-
#
import uuid
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework.views import APIView, Response
from rest_framework.generics import (
    ListAPIView, get_object_or_404
)

from orgs.utils import tmp_to_root_org
from applications.models import Application
from perms.utils.application.permission import (
    has_application_system_permission,
    get_application_system_users_id
)
from perms.api.asset.user_permission.mixin import RoleAdminMixin, RoleUserMixin
from common.permissions import IsOrgAdminOrAppUser
from perms.hands import User, SystemUser
from perms import serializers


__all__ = [
    'UserGrantedApplicationSystemUsersApi',
    'MyGrantedApplicationSystemUsersApi',
    'ValidateUserApplicationPermissionApi'
]


class GrantedApplicationSystemUsersMixin(ListAPIView):
    serializer_class = serializers.ApplicationSystemUserSerializer
    only_fields = serializers.ApplicationSystemUserSerializer.Meta.only_fields
    user: None

    def get_application_system_users_id(self, application):
        return get_application_system_users_id(self.user, application)

    def get_queryset(self):
        application_id = self.kwargs.get('application_id')
        application = get_object_or_404(Application, id=application_id)
        system_users_id = self.get_application_system_users_id(application)
        system_users = SystemUser.objects.filter(id__in=system_users_id)\
            .only(*self.only_fields).order_by('priority')
        return system_users


class UserGrantedApplicationSystemUsersApi(RoleAdminMixin, GrantedApplicationSystemUsersMixin):
    pass


class MyGrantedApplicationSystemUsersApi(RoleUserMixin, GrantedApplicationSystemUsersMixin):
    pass


@method_decorator(tmp_to_root_org(), name='get')
class ValidateUserApplicationPermissionApi(APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id', '')
        application_id = request.query_params.get('application_id', '')
        system_user_id = request.query_params.get('system_user_id', '')

        try:
            user_id = uuid.UUID(user_id)
            application_id = uuid.UUID(application_id)
            system_user_id = uuid.UUID(system_user_id)
        except ValueError:
            return Response({'msg': False}, status=403)

        user = get_object_or_404(User, id=user_id)
        application = get_object_or_404(Application, id=application_id)
        system_user = get_object_or_404(SystemUser, id=system_user_id)

        if has_application_system_permission(user, application, system_user):
            return Response({'msg': True}, status=200)

        return Response({'msg': False}, status=403)

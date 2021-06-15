# coding: utf-8
#

from rest_framework import generics
from django.conf import settings

from ..hands import IsOrgAdminOrAppUser, IsOrgAdmin, NeedMFAVerify
from .. import serializers
from ..models import Application, ApplicationUser
from perms.models import ApplicationPermission


class ApplicationUserListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin, )
    filterset_fields = ('name', 'username')
    search_fields = filterset_fields
    serializer_class = serializers.ApplicationUserSerializer
    _application = None

    @property
    def application(self):
        if self._application is None:
            app_id = self.request.query_params.get('application_id')
            if app_id:
                self._application = Application.objects.get(id=app_id)
        return self._application

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({
            'application': self.application
        })
        return context

    def get_queryset(self):
        queryset = ApplicationUser.objects.none()
        if not self.application:
            return queryset
        system_user_ids = ApplicationPermission.objects.filter(applications=self.application)\
            .values_list('system_users', flat=True)
        if not system_user_ids:
            return queryset
        queryset = ApplicationUser.objects.filter(id__in=system_user_ids)
        return queryset


class ApplicationUserAuthInfoListApi(ApplicationUserListApi):
    serializer_class = serializers.ApplicationUserWithAuthInfoSerializer
    http_method_names = ['get']
    permission_classes = [IsOrgAdminOrAppUser]

    def get_permissions(self):
        if settings.SECURITY_VIEW_AUTH_NEED_MFA:
            self.permission_classes = [IsOrgAdminOrAppUser, NeedMFAVerify]
        return super().get_permissions()

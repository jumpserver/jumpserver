# coding: utf-8
#

from orgs.mixins.api import OrgBulkModelViewSet
from rest_framework import generics

from ..hands import IsOrgAdminOrAppUser, IsOrgAdmin
from .. import models, serializers
from ..models import Application
from assets.models import SystemUser
from assets.serializers import SystemUserListSerializer
from perms.models import ApplicationPermission
from ..const import ApplicationCategoryChoices


__all__ = ['ApplicationViewSet', 'ApplicationUserListApi']


class ApplicationViewSet(OrgBulkModelViewSet):
    model = Application
    filterset_fields = ('name', 'type', 'category')
    search_fields = filterset_fields
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.ApplicationSerializer


class ApplicationUserListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin, )
    filterset_fields = ('name', 'username')
    search_fields = filterset_fields
    serializer_class = SystemUserListSerializer

    def get_application(self):
        application = None
        app_id = self.request.query_params.get('application_id')
        if app_id:
            application = Application.objects.get(id=app_id)
        return application

    def get_queryset(self):
        queryset = SystemUser.objects.none()
        application = self.get_application()
        if not application:
            return queryset
        system_user_ids = ApplicationPermission.objects.filter(applications=application)\
            .values_list('system_users', flat=True)
        if not system_user_ids:
            return queryset
        queryset = SystemUser.objects.filter(id__in=system_user_ids)
        return queryset

# -*- coding: utf-8 -*-
#

from rest_framework_bulk import BulkModelViewSet
from rest_framework import generics, status
from rest_framework.views import Response

from common.mixins import IDInFilterMixin
from common.permissions import IsSuperUserOrAppUser
from .models import Organization
from .serializers import OrgSerializer, OrgUpdateAdminSerializer, \
    OrgUpdateUserSerializer
from users.models import User, UserGroup
from assets.models import Asset, Domain, AdminUser, SystemUser, Label
from perms.models import AssetPermission
from orgs.utils import current_org
from common.utils import get_logger

logger = get_logger(__file__)


class OrgViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrgSerializer
    permission_classes = (IsSuperUserOrAppUser,)
    org = None

    def get_data_from_model(self, model):
        if model == User:
            data = model.objects.filter(orgs__id=self.org.id)
        else:
            data = model.objects.filter(org_id=self.org.id)
        return data

    def destroy(self, request, *args, **kwargs):
        self.org = self.get_object()
        models = [
            User, UserGroup,
            Asset, Domain, AdminUser, SystemUser, Label,
            AssetPermission,
        ]
        for model in models:
            data = self.get_data_from_model(model)
            if data:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            if str(current_org) == str(self.org):
                return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
            self.org.delete()
            return Response({'msg': True}, status=status.HTTP_200_OK)


class OrgUpdateUsersApi(generics.RetrieveUpdateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrgUpdateUserSerializer
    permission_classes = (IsSuperUserOrAppUser, )
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def post(self, *args, **kwargs):
        org = self.get_object()

        users = []
        users_id = self.request.data.get('users', [])
        for _id in users_id:
            try:
                user = User.objects.get(pk=_id)
                users.append(user)
            except Exception as e:
                logger.error(e)
                data = {"error": "User({}) not found.".format(_id)}
                return Response(data=data, status=status.HTTP_400_BAD_REQUEST)

        for user in users:
            org.users.add(user)

        users = [user.id for user in org.users.all()]
        data = {"id": org.id, "users": users}
        return Response(data=data, status=status.HTTP_200_OK)


class OrgUpdateAdminsApi(generics.RetrieveUpdateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrgUpdateAdminSerializer
    permission_classes = (IsSuperUserOrAppUser, )
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def post(self, *args, **kwargs):
        org = self.get_object()

        users = []
        admins_id = self.request.data.get('admins', [])
        for _id in admins_id:
            try:
                user = User.objects.get(pk=_id)
                users.append(user)
            except Exception as e:
                logger.error(e)
                data = {"error": "Admin user({}) not found.".format(_id)}
                return Response(data=data, status=status.HTTP_400_BAD_REQUEST)

        for user in users:
            org.admins.add(user)

        admins = [admin.id for admin in org.admins.all()]
        data = {"id": org.id, "admins": admins}
        return Response(data=data, status=status.HTTP_200_OK)

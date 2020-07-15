# -*- coding: utf-8 -*-
#

from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from rest_framework import status, generics
from rest_framework.views import Response
from rest_framework_bulk import BulkModelViewSet

from common.permissions import IsSuperUserOrAppUser
from .models import Organization
from .serializers import OrgSerializer, OrgReadSerializer, \
    OrgMembershipUserSerializer, OrgMembershipAdminSerializer, \
    OrgAllUserSerializer, OrgRetrieveSerializer
from users.models import User, UserGroup
from assets.models import Asset, Domain, AdminUser, SystemUser, Label
from perms.models import AssetPermission
from orgs.utils import current_org
from common.utils import get_logger
from .mixins.api import OrgMembershipModelViewSetMixin

logger = get_logger(__file__)


class OrgViewSet(BulkModelViewSet):
    filter_fields = ('name',)
    search_fields = ('name', 'comment')
    queryset = Organization.objects.all()
    serializer_class = OrgSerializer
    permission_classes = (IsSuperUserOrAppUser,)
    org = None

    def get_serializer_class(self):
        mapper = {
            'list': OrgReadSerializer,
            'retrieve': OrgRetrieveSerializer
        }
        return mapper.get(self.action, super().get_serializer_class())

    def get_data_from_model(self, model):
        if model == User:
            data = model.objects.filter(related_user_orgs__id=self.org.id)
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
                msg = _('Organization contains undeleted resources')
                return Response(data={'error': msg}, status=status.HTTP_403_FORBIDDEN)
        else:
            if str(current_org) == str(self.org):
                msg = _('The current organization cannot be deleted')
                return Response(data={'error': msg}, status=status.HTTP_403_FORBIDDEN)
            self.org.delete()
            return Response({'msg': True}, status=status.HTTP_200_OK)


class OrgMembershipAdminsViewSet(OrgMembershipModelViewSetMixin, BulkModelViewSet):
    serializer_class = OrgMembershipAdminSerializer
    membership_class = Organization.admins.through
    permission_classes = (IsSuperUserOrAppUser, )


class OrgMembershipUsersViewSet(OrgMembershipModelViewSetMixin, BulkModelViewSet):
    serializer_class = OrgMembershipUserSerializer
    membership_class = Organization.users.through
    permission_classes = (IsSuperUserOrAppUser, )


class OrgAllUserListApi(generics.ListAPIView):
    permission_classes = (IsSuperUserOrAppUser,)
    serializer_class = OrgAllUserSerializer
    filter_fields = ("username", "name")
    search_fields = filter_fields

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        org = get_object_or_404(Organization, pk=pk)
        users = org.get_org_users().only(*self.serializer_class.Meta.only_fields)
        return users

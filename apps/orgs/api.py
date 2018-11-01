# -*- coding: utf-8 -*-
#

from rest_framework import status
from rest_framework.views import Response
from rest_framework_bulk import BulkModelViewSet

from common.permissions import IsSuperUserOrAppUser
from .models import Organization
from .serializers import OrgSerializer, OrgReadSerializer, \
    OrgMembershipUserSerializer, OrgMembershipAdminSerializer
from users.models import User, UserGroup
from assets.models import Asset, Domain, AdminUser, SystemUser, Label
from perms.models import AssetPermission
from orgs.utils import current_org
from common.utils import get_logger

logger = get_logger(__file__)


class OrgViewSet(BulkModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrgSerializer
    permission_classes = (IsSuperUserOrAppUser,)
    org = None

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return OrgReadSerializer
        else:
            return super().get_serializer_class()

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


class OrgMembershipModelViewSetMixin(BulkModelViewSet):
    org = None
    membership_class = None
    permission_classes = (IsSuperUserOrAppUser, )

    def dispatch(self, request, *args, **kwargs):
        self.org = Organization.objects.get(pk=kwargs.get('org_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['org'] = self.org
        return context

    def get_queryset(self):
        return self.membership_class.objects.filter(organization=self.org)

    def destroy(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs.get('pk'))
        membership = Organization.admins.through.objects.filter(
            organization=self.org, user=user
        )
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrgMembershipAdminsViewSet(OrgMembershipModelViewSetMixin):
    serializer_class = OrgMembershipAdminSerializer
    membership_class = Organization.admins.through


class OrgMembershipUsersViewSet(OrgMembershipModelViewSetMixin):
    serializer_class = OrgMembershipUserSerializer
    membership_class = Organization.users.through

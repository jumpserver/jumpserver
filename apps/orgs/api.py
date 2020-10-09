# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from django.db.models import Q
from rest_framework import status, generics
from rest_framework.views import Response
from rest_framework_bulk import BulkModelViewSet
from rest_framework.mixins import CreateModelMixin

from common.permissions import IsSuperUserOrAppUser
from common.drf.api import JMSBulkRelationModelViewSet
from .models import Organization, ROLE
from .serializers import (
    OrgSerializer, OrgReadSerializer,
    OrgRetrieveSerializer, OrgMemberSerializer
)
from users.models import User, UserGroup
from assets.models import Asset, Domain, AdminUser, SystemUser, Label
from perms.models import AssetPermission
from orgs.utils import current_org
from common.utils import get_logger
from .filters import OrgMemberRelationFilterSet
from .models import OrganizationMember


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
            data = model.objects.filter(orgs__id=self.org.id, m2m_org_members__role=ROLE.USER)
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


class OrgMemberRelationBulkViewSet(JMSBulkRelationModelViewSet):
    permission_classes = (IsSuperUserOrAppUser,)
    m2m_field = Organization.members.field
    serializer_class = OrgMemberSerializer
    filterset_class = OrgMemberRelationFilterSet

    @staticmethod
    def clear_request_data(request):
        data = request.data

        ignore_already_exist = request.query_params.get('ignore_already_exist')
        if not ignore_already_exist:
            return data

        query_params = Q()
        for _data in data:
            query_fields = {}
            org = _data.get('org')
            if org:
                query_fields.update({'org': org})
            user = _data.get('user')
            if user:
                query_fields.update({'user': user})
            role = _data.get('role')
            if role:
                query_fields.update({'role': role})
            query_params |= Q(**query_fields)

        if not query_params:
            return data

        members = OrganizationMember.objects.filter(query_params)
        members = [
            {'org': str(member.org_id), 'user': str(member.user_id), 'role': member.role}
            for member in members
        ]
        if not members:
            return data

        for member in members:
            if member in data:
                data.remove(member)
        return data

    def create(self, request, *args, **kwargs):
        bulk = isinstance(request.data, list)

        if not bulk:
            return CreateModelMixin.create(self, request, *args, **kwargs)

        else:
            data = self.clear_request_data(request)
            serializer = self.get_serializer(data=data, many=True)
            serializer.is_valid(raise_exception=True)
            self.perform_bulk_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_bulk_destroy(self, queryset):
        objs = list(queryset.all().prefetch_related('user', 'org'))
        queryset.delete()
        self.send_m2m_changed_signal(objs, action='post_remove')

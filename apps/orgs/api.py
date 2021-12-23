# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from rest_framework_bulk import BulkModelViewSet
from rest_framework.generics import RetrieveAPIView
from rest_framework.exceptions import PermissionDenied

from common.permissions import IsSuperUserOrAppUser, IsValidUser, UserCanAnyPermCurrentOrg
from common.drf.api import JMSBulkRelationModelViewSet
from .models import Organization
from .serializers import (
    OrgSerializer, OrgMemberSerializer, CurrentOrgSerializer
)
from users.models import User, UserGroup
from assets.models import (
    Asset, Domain, AdminUser, SystemUser, Label, Node, Gateway,
    CommandFilter, CommandFilterRule, GatheredUser
)
from applications.models import Application
from perms.models import AssetPermission, ApplicationPermission
from orgs.utils import current_org, tmp_to_root_org
from common.utils import get_logger
from .filters import OrgMemberRelationFilterSet


logger = get_logger(__file__)


# 部分 org 相关的 model，需要清空这些数据之后才能删除该组织
org_related_models = [
    User, UserGroup, Asset, Label, Domain, Gateway, Node, AdminUser, SystemUser, Label,
    CommandFilter, CommandFilterRule, GatheredUser,
    AssetPermission, ApplicationPermission,
    Application,
]


class OrgViewSet(BulkModelViewSet):
    filterset_fields = ('name',)
    search_fields = ('name', 'comment')
    queryset = Organization.objects.all()
    serializer_class = OrgSerializer
    permission_classes = (IsSuperUserOrAppUser,)

    def get_serializer_class(self):
        mapper = {
            'list': OrgSerializer,
            'retrieve': OrgSerializer
        }
        return mapper.get(self.action, super().get_serializer_class())

    @tmp_to_root_org()
    def get_data_from_model(self, org, model):
        if model == User:
            data = model.get_org_users(org=org)
        elif model == Node:
            # 根节点不能手动删除，所以排除检查
            data = model.objects.filter(org_id=org.id).exclude(parent_key='', key__regex=r'^[0-9]+$')
        else:
            data = model.objects.filter(org_id=org.id)
        return data

    def allow_bulk_destroy(self, qs, filtered):
        return False

    def perform_destroy(self, instance):
        if str(current_org) == str(instance):
            msg = _('The current organization ({}) cannot be deleted'.format(current_org))
            raise PermissionDenied(detail=msg)

        for model in org_related_models:
            data = self.get_data_from_model(instance, model)
            if not data:
                continue
            msg = _(
                'The organization have resource ({}) cannot be deleted'
            ).format(model._meta.verbose_name)
            raise PermissionDenied(detail=msg)

        super().perform_destroy(instance)


class OrgMemberRelationBulkViewSet(JMSBulkRelationModelViewSet):
    permission_classes = (IsSuperUserOrAppUser,)
    m2m_field = Organization.members.field
    serializer_class = OrgMemberSerializer
    filterset_class = OrgMemberRelationFilterSet
    search_fields = ('user__name', 'user__username', 'org__name')

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.exclude(user__is_app=True)
        return queryset

    def perform_bulk_destroy(self, queryset):
        objs = list(queryset.all().prefetch_related('user', 'org'))
        queryset.delete()
        self.send_m2m_changed_signal(objs, action='post_remove')


class CurrentOrgDetailApi(RetrieveAPIView):
    serializer_class = CurrentOrgSerializer
    permission_classes = (IsValidUser, UserCanAnyPermCurrentOrg)

    def get_object(self):
        return current_org

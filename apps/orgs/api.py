# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from django.conf import settings
from rest_framework_bulk import BulkModelViewSet
from rest_framework.generics import RetrieveAPIView
from rest_framework.exceptions import PermissionDenied

from common.permissions import IsValidUser
from .models import Organization
from .serializers import (
    OrgSerializer, CurrentOrgSerializer
)
from users.models import User, UserGroup
from assets.models import (
    Asset, Domain, SystemUser, Label, Node, Gateway,
    CommandFilter, CommandFilterRule, GatheredUser
)
from applications.models import Application
from perms.models import AssetPermission, ApplicationPermission
from orgs.utils import current_org, tmp_to_root_org
from common.utils import get_logger


logger = get_logger(__file__)


# 部分 org 相关的 model，需要清空这些数据之后才能删除该组织
org_related_models = [
    User, UserGroup, Asset, Label, Domain, Gateway, Node, SystemUser, Label,
    CommandFilter, CommandFilterRule, GatheredUser,
    AssetPermission, ApplicationPermission,
    Application,
]


class OrgViewSet(BulkModelViewSet):
    filterset_fields = ('name',)
    search_fields = ('name', 'comment')
    queryset = Organization.objects.all()
    serializer_class = OrgSerializer
    ordering_fields = ('name',)
    ordering = ('name', )

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
            msg = _('The current organization ({}) cannot be deleted').format(current_org)
            raise PermissionDenied(detail=msg)

        if str(instance.id) == settings.AUTH_LDAP_SYNC_ORG_ID:
            msg = _(
                'LDAP synchronization is set to the current organization. Please switch to another organization before deleting'
            )
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


class CurrentOrgDetailApi(RetrieveAPIView):
    serializer_class = CurrentOrgSerializer
    permission_classes = (IsValidUser,)

    def get_object(self):
        return current_org

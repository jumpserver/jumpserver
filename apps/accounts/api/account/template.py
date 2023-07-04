from django_filters import rest_framework as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import serializers
from accounts.models import AccountTemplate
from assets.const import Protocol
from common.drf.filters import BaseFilterSet
from common.permissions import UserConfirmation, ConfirmType
from common.views.mixins import RecordViewLogMixin
from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission


class AccountTemplateFilterSet(BaseFilterSet):
    protocols = drf_filters.CharFilter(method='filter_protocols')

    class Meta:
        model = AccountTemplate
        fields = ('username', 'name')

    @staticmethod
    def filter_protocols(queryset, name, value):
        secret_types = set()
        protocols = value.split(',')
        protocol_secret_type_map = Protocol.settings()
        for p in protocols:
            if p not in protocol_secret_type_map:
                continue
            _st = protocol_secret_type_map[p].get('secret_types', [])
            secret_types.update(_st)
        if not secret_types:
            secret_types = ['password']
        queryset = queryset.filter(secret_type__in=secret_types)
        return queryset


class AccountTemplateViewSet(OrgBulkModelViewSet):
    model = AccountTemplate
    filterset_class = AccountTemplateFilterSet
    search_fields = ('username', 'name')
    serializer_classes = {
        'default': serializers.AccountTemplateSerializer,
    }
    rbac_perms = {
        'su_from_account_templates': 'accounts.view_accounttemplate',
    }

    @action(methods=['get'], detail=False, url_path='su-from-account-templates')
    def su_from_account_templates(self, request, *args, **kwargs):
        pk = request.query_params.get('template_id')
        templates = AccountTemplate.get_su_from_account_templates(pk)
        templates = self.filter_queryset(templates)
        serializer = self.get_serializer(templates, many=True)
        return Response(data=serializer.data)


class AccountTemplateSecretsViewSet(RecordViewLogMixin, AccountTemplateViewSet):
    serializer_classes = {
        'default': serializers.AccountTemplateSecretSerializer,
    }
    http_method_names = ['get', 'options']
    permission_classes = [RBACPermission, UserConfirmation.require(ConfirmType.MFA)]
    rbac_perms = {
        'list': 'accounts.view_accounttemplatesecret',
        'retrieve': 'accounts.view_accounttemplatesecret',
    }

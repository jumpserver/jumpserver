from rbac.permissions import RBACPermission
from common.permissions import UserConfirmation, ConfirmType

from common.views.mixins import RecordViewLogMixin
from orgs.mixins.api import OrgBulkModelViewSet
from accounts import serializers
from accounts.models import AccountTemplate


class AccountTemplateViewSet(OrgBulkModelViewSet):
    model = AccountTemplate
    filterset_fields = ("username", 'name')
    search_fields = ('username', 'name')
    serializer_classes = {
        'default': serializers.AccountTemplateSerializer
    }


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

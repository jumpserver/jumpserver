from assets import serializers
from assets.models import AccountTemplate
from common.mixins import RecordViewLogMixin
from orgs.mixins.api import OrgBulkModelViewSet


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
    # Todo: 记得打开
    # permission_classes = [RBACPermission, UserConfirmation.require(ConfirmType.MFA)]
    rbac_perms = {
        'list': 'assets.view_accounttemplatesecret',
        'retrieve': 'assets.view_accounttemplatesecret',
    }

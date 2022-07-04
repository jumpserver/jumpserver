from django.db.models import F

from assets.api.accounts import (
    AccountFilterSet, AccountViewSet, AccountSecretsViewSet
)
from common.mixins import RecordViewLogMixin
from .. import serializers
from ..models import AuthBook

__all__ = ['AccountHistoryViewSet', 'AccountHistorySecretsViewSet']


class AccountHistoryFilterSet(AccountFilterSet):
    class Meta:
        model = AuthBook.history.model
        fields = AccountFilterSet.Meta.fields


class AccountHistoryViewSet(AccountViewSet):
    model = AuthBook.history.model
    filterset_class = AccountHistoryFilterSet
    serializer_classes = {
        'default': serializers.AccountHistorySerializer,
    }
    rbac_perms = {
        'list': 'assets.view_assethistoryaccount',
        'retrieve': 'assets.view_assethistoryaccount',
    }

    http_method_names = ['get', 'options']

    def get_queryset(self):
        queryset = AuthBook.get_queryset(is_history_model=True)
        return queryset


class AccountHistorySecretsViewSet(RecordViewLogMixin, AccountHistoryViewSet):
    serializer_classes = {
        'default': serializers.AccountHistorySecretSerializer
    }
    http_method_names = ['get']
    permission_classes = AccountSecretsViewSet.permission_classes
    rbac_perms = {
        'list': 'assets.view_assethistoryaccountsecret',
        'retrieve': 'assets.view_assethistoryaccountsecret',
    }

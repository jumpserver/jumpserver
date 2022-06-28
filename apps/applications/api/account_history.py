# coding: utf-8
#
from django.db.models import F

from common.mixins import RecordViewLogMixin
from .account import (
    AccountFilterSet, ApplicationAccountViewSet
)
from ..models import Account
from .. import serializers


class AccountHistoryFilterSet(AccountFilterSet):
    class Meta:
        model = Account.history.model
        fields = AccountFilterSet.Meta.fields
        read_only_fields = fields


class ApplicationAccountHistoryViewSet(ApplicationAccountViewSet):
    model = Account.history.model
    filterset_class = AccountHistoryFilterSet
    serializer_class = serializers.AppAccountHistorySerializer

    def get_queryset(self):
        queryset = self.model.objects.all() \
            .annotate(type=F('app__type')) \
            .annotate(app_display=F('app__name')) \
            .annotate(systemuser_display=F('systemuser__name')) \
            .annotate(category=F('app__category'))
        return queryset


class ApplicationAccountHistorySecretViewSet(RecordViewLogMixin, ApplicationAccountHistoryViewSet):
    serializer_class = serializers.AppAccountHistorySecretSerializer
    rbac_perms = {
        'retrieve': 'applications.view_applicationaccountsecret',
        'list': 'applications.view_applicationaccountsecret',
    }

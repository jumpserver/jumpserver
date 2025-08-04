# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.db.models import Count, F, Value
from django.db.models.functions import Concat
from django.http import JsonResponse
from rest_framework.views import APIView

from accounts.models import ChangeSecretAutomation, PushAccountAutomation, BackupAccountAutomation, \
    CheckAccountAutomation, GatherAccountsAutomation, AutomationExecution
from assets.const import Connectivity
from common.permissions import IsValidLicense
from rbac.permissions import RBACPermission
from reports.api.assets.base import group_stats
from reports.mixins import DateRangeMixin

__all__ = ['AccountAutomationApi']


class AccountAutomationApi(DateRangeMixin, APIView):
    http_method_names = ['get']
    # TODO: Define the required RBAC permissions for this API
    rbac_perms = {
        'GET': 'accounts.view_account',
    }
    permission_classes = [RBACPermission, IsValidLicense]

    @property
    def change_secret_qs(self):
        return ChangeSecretAutomation.objects.all()

    @property
    def push_qs(self):
        return PushAccountAutomation.objects.all()

    @property
    def backup_qs(self):
        return BackupAccountAutomation.objects.all()

    @property
    def check_qs(self):
        return CheckAccountAutomation.objects.all()

    @property
    def collect_qs(self):
        return GatherAccountsAutomation.objects.all()

    @property
    def execution_qs(self):
        return AutomationExecution.objects.all()

    def get_change_secret_account_metrics(self):
        filtered_queryset = self.filter_by_date_range(self.base_qs, 'date_change_secret')

        data = defaultdict(set)
        for t, _id in filtered_queryset.values_list('date_change_secret', 'id'):
            date_str = str(t.date())
            data[date_str].add(_id)

        metrics = [len(data.get(str(d), set())) for d in self.date_range_list]
        return metrics

    def get_execution_metrics(self):
        filtered_queryset = self.filter_by_date_range(self.base_qs, 'date_change_secret')

        data = defaultdict(set)
        for t, _id in filtered_queryset.values_list('date_change_secret', 'id'):
            date_str = str(t.date())
            data[date_str].add(_id)

        metrics = [len(data.get(str(d), set())) for d in self.date_range_list]
        return metrics

    def get(self, request, *args, **kwargs):
        stats = {}
        stats['change_secret'] = self.change_secret_qs.count()
        stats['push'] = self.push_qs.count()
        stats['backup'] = self.backup_qs.count()
        stats['check'] = self.check_qs.count()
        stats['collect'] = self.collect_qs.count()

        AutomationExecution.objects.all()

        source_pie_data = [
            {'name': str(source), 'value': total}
            for source, total in
            qs.values('source').annotate(
                total=Count(1)
            ).values_list('source', 'total')
        ]

        by_connectivity = group_stats(
            qs, 'label', 'connectivity', Connectivity.as_dict(),
        )

        top_assets = qs.values('asset__name') \
                         .annotate(account_count=Count('id')) \
                         .order_by('-account_count')[:10]

        top_version_accounts = qs.annotate(
            display_key=Concat(
                F('asset__name'),
                Value('（'),
                F('username'),
                Value('）')
            )
        ).values('display_key', 'version').order_by('-version')[:10]

        payload = {
            'account_stats': stats,
            'top_assets': list(top_assets),
            'top_version_accounts': list(top_version_accounts),
            'source_pie': source_pie_data,
            'by_connectivity': by_connectivity,
            'change_secret_account_metrics': {
                'dates_metrics_date': self.dates_metrics_date,
                'dates_metrics_total': self.get_change_secret_account_metrics(),
            }
        }
        return JsonResponse(payload, status=200)

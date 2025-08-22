# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView

from accounts.const import AutomationTypes
from accounts.models import ChangeSecretAutomation, PushAccountAutomation, BackupAccountAutomation, \
    CheckAccountAutomation, GatherAccountsAutomation, AutomationExecution
from common.permissions import IsValidLicense
from rbac.permissions import RBACPermission
from reports.mixins import DateRangeMixin

__all__ = ['AccountAutomationApi']


class AccountAutomationApi(DateRangeMixin, APIView):
    http_method_names = ['get']
    rbac_perms = {
        'GET': 'rbac.view_accountautomationreport',
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

    def get_execution_metrics(self):
        executions = AutomationExecution.objects.filter(type__in=AutomationTypes.values)
        qs = self.filter_by_date_range(executions, 'date_start')

        types = set()
        data = defaultdict(lambda: defaultdict(int))
        for obj in qs:
            tp = obj.type
            if not tp:
                continue
            types.add(tp)

            dt = obj.date_start
            dt_local = timezone.localtime(dt)
            date_str = str(dt_local.date())
            data[date_str][tp] += 1

        tp_map = defaultdict(list)
        for d in self.date_range_list:
            tp_data = data.get(str(d), {})
            for tp in types:
                tp_map[tp].append(tp_data.get(tp, 0))

        metrics = {}
        for tp, values in tp_map.items():
            if tp == AutomationTypes.change_secret:
                _tp = _('Account change secret')
            else:
                _tp = AutomationTypes(tp).label
            metrics[str(_tp)] = values

        return metrics

    def get(self, request, *args, **kwargs):
        stats = {
            'push': self.push_qs.count(),
            'check': self.check_qs.count(),
            'backup': self.backup_qs.count(),
            'collect': self.collect_qs.count(),
            'change_secret': self.change_secret_qs.count(),
        }

        payload = {
            'automation_stats': stats,
            'execution_metrics': {
                'dates_metrics_date': self.dates_metrics_date,
                'data': self.get_execution_metrics()
            },
        }
        return JsonResponse(payload, status=200)

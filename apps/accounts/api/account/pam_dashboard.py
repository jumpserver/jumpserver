# -*- coding: utf-8 -*-
#
from django.db.models import Count, F, Q
from django.http.response import JsonResponse
from rest_framework.views import APIView

from accounts.models import (
    Account, RiskChoice, GatherAccountsAutomation,
    PushAccountAutomation, BackupAccountAutomation,
    AccountRisk, IntegrationApplication, ChangeSecretAutomation
)
from assets.const import AllTypes
from common.utils.timezone import local_monday

__all__ = ['PamDashboardApi']


class PamDashboardApi(APIView):
    http_method_names = ['get']
    rbac_perms = {
        'GET': 'accounts.view_account',
    }

    @staticmethod
    def get_type_to_accounts():
        result = Account.objects.annotate(type=F('asset__platform__type')). \
            values('type').order_by('type').annotate(total=Count(1))
        all_types_dict = dict(AllTypes.choices())

        result = [
            {
                **i,
                'label': all_types_dict.get(i['type'], i['type'])
            }
            for i in result
        ]
        return result

    def get(self, request, *args, **kwargs):
        monday_time = local_monday()
        query_params = self.request.query_params

        _all = query_params.get('all')

        agg_map = {
            'total_accounts': (
                'total_count',
                Count('id')
            ),
            'total_privileged_accounts': (
                'privileged_count',
                Count('id', filter=Q(privileged=True))
            ),
            'total_connectivity_ok_accounts': (
                'connectivity_ok_count',
                Count('id', filter=Q(connectivity='ok'))
            ),
            'total_secret_reset_accounts': (
                'secret_reset_count',
                Count('id', filter=Q(secret_reset=True))
            ),
            'total_unavailable_accounts': (
                'unavailable_count',
                Count('id', filter=Q(is_active=False))
            ),
            'total_week_add_accounts': (
                'week_add_count',
                Count('id', filter=Q(date_created__gte=monday_time))
            ),
        }

        aggregations = {}
        for param_key, (agg_key, agg_expr) in agg_map.items():
            if _all or query_params.get(param_key):
                aggregations[agg_key] = agg_expr

        data = {}
        if aggregations:
            account_stats = Account.objects.aggregate(**aggregations)
            for param_key, (agg_key, __) in agg_map.items():
                if agg_key in account_stats:
                    data[param_key] = account_stats[agg_key]

            if (_all or query_params.get('total_ordinary_accounts')):
                if 'total_count' in account_stats and 'privileged_count' in account_stats:
                    data['total_ordinary_accounts'] = \
                        account_stats['total_count'] - account_stats['privileged_count']

        if _all or query_params.get('total_unmanaged_accounts'):
            data['total_unmanaged_accounts'] = Account.get_risks(
                risk_type=RiskChoice.new_found).count()

        if _all or query_params.get('total_long_time_no_login_accounts'):
            data['total_long_time_no_login_accounts'] = Account.get_risks(
                risk_type=RiskChoice.long_time_no_login).count()

        if _all or query_params.get('total_weak_password_accounts'):
            data['total_weak_password_accounts'] = Account.get_risks(
                risk_type=RiskChoice.weak_password).count()

        if _all or query_params.get('total_long_time_change_password_accounts'):
            data['total_long_time_change_password_accounts'] = Account.get_risks(
                risk_type=RiskChoice.long_time_password).count()

        if _all or query_params.get('total_leaked_password_accounts'):
            data['total_leaked_password_accounts'] = Account.get_risks(
                risk_type=RiskChoice.leaked_password).count()

        if _all or query_params.get('total_repeated_password_accounts'):
            data['total_repeated_password_accounts'] = Account.get_risks(
                risk_type=RiskChoice.repeated_password).count()

        if _all or query_params.get('total_count_type_to_accounts'):
            data.update({
                'total_count_type_to_accounts': self.get_type_to_accounts(),
            })

        if _all or query_params.get('total_count_change_secret_automation'):
            data.update({
                'total_count_change_secret_automation': ChangeSecretAutomation.objects.count()
            })

        if _all or query_params.get('total_count_gathered_account_automation'):
            data.update({
                'total_count_gathered_account_automation': GatherAccountsAutomation.objects.count()
            })

        if _all or query_params.get('total_count_push_account_automation'):
            data.update({
                'total_count_push_account_automation': PushAccountAutomation.objects.count()
            })

        if _all or query_params.get('total_count_backup_account_automation'):
            data.update({
                'total_count_backup_account_automation': BackupAccountAutomation.objects.count()
            })

        if _all or query_params.get('total_count_risk_account'):
            data.update({
                'total_count_risk_account': AccountRisk.objects.count()
            })

        if _all or query_params.get('total_count_integration_application'):
            data.update({
                'total_count_integration_application': IntegrationApplication.objects.count()
            })

        return JsonResponse(data, status=200)

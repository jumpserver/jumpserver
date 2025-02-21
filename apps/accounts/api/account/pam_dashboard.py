# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.db.models import Count, F, Q
from django.http.response import JsonResponse
from rest_framework.views import APIView

from accounts.models import (
    Account, GatherAccountsAutomation,
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
        result = Account.objects.annotate(type=F('asset__platform__type')) \
            .values('type').order_by('type').annotate(total=Count(1))
        all_types_dict = dict(AllTypes.choices())

        return [
            {**i, 'label': all_types_dict.get(i['type'], i['type'])}
            for i in result
        ]

    @staticmethod
    def get_account_risk_data(_all, query_params):
        agg_map = {
            'total_long_time_no_login_accounts': ('long_time_no_login_count', Q(risk='long_time_no_login')),
            'total_new_found_accounts': ('new_found_count', Q(risk='new_found')),
            'total_group_changed_accounts': ('group_changed_count', Q(risk='group_changed')),
            'total_sudo_changed_accounts': ('sudo_changed_count', Q(risk='sudo_changed')),
            'total_authorized_keys_changed_accounts': (
                'authorized_keys_changed_count', Q(risk='authorized_keys_changed')),
            'total_account_deleted_accounts': ('account_deleted_count', Q(risk='account_deleted')),
            'total_password_expired_accounts': ('password_expired_count', Q(risk='password_expired')),
            'total_long_time_password_accounts': ('long_time_password_count', Q(risk='long_time_password')),
            'total_weak_password_accounts': ('weak_password_count', Q(risk='weak_password')),
            'total_leaked_password_accounts': ('leaked_password_count', Q(risk='leaked_password')),
            'total_repeated_password_accounts': ('repeated_password_count', Q(risk='repeated_password')),
            'total_password_error_accounts': ('password_error_count', Q(risk='password_error')),
            'total_no_admin_account_accounts': ('no_admin_account_count', Q(risk='no_admin_account')),
        }

        aggregations = {
            agg_key: Count('account_id', distinct=True, filter=agg_filter)
            for param_key, (agg_key, agg_filter) in agg_map.items()
            if _all or query_params.get(param_key)
        }

        data = {}
        if aggregations:
            account_stats = AccountRisk.objects.filter(account__isnull=False).aggregate(**aggregations)
            data = {param_key: account_stats.get(agg_key) for param_key, (agg_key, _) in agg_map.items() if
                    agg_key in account_stats}

        return data

    @staticmethod
    def get_account_data(_all, query_params):
        agg_map = {
            'total_accounts': ('total_count', Count('id')),
            'total_privileged_accounts': ('privileged_count', Count('id', filter=Q(privileged=True))),
            'total_connectivity_ok_accounts': ('connectivity_ok_count', Count('id', filter=Q(connectivity='ok'))),
            'total_secret_reset_accounts': ('secret_reset_count', Count('id', filter=Q(secret_reset=True))),
            'total_valid_accounts': ('valid_count', Count('id', filter=Q(is_active=True))),
            'total_week_add_accounts': ('week_add_count', Count('id', filter=Q(date_created__gte=local_monday()))),
        }

        aggregations = {
            agg_key: agg_expr
            for param_key, (agg_key, agg_expr) in agg_map.items()
            if _all or query_params.get(param_key)
        }

        data = {}
        account_stats = Account.objects.aggregate(**aggregations)
        for param_key, (agg_key, __) in agg_map.items():
            if agg_key in account_stats:
                data[param_key] = account_stats[agg_key]

        if _all or query_params.get('total_ordinary_accounts'):
            if 'total_count' in account_stats and 'privileged_count' in account_stats:
                data['total_ordinary_accounts'] = \
                    account_stats['total_count'] - account_stats['privileged_count']

        return data

    @staticmethod
    def get_automation_counts(_all, query_params):
        automation_counts = defaultdict(int)
        automation_models = {
            'total_count_change_secret_automation': ChangeSecretAutomation,
            'total_count_gathered_account_automation': GatherAccountsAutomation,
            'total_count_push_account_automation': PushAccountAutomation,
            'total_count_backup_account_automation': BackupAccountAutomation,
            'total_count_integration_application': IntegrationApplication,
        }

        for param_key, model in automation_models.items():
            if _all or query_params.get(param_key):
                automation_counts[param_key] = model.objects.count()

        return automation_counts

    def get(self, request, *args, **kwargs):
        query_params = self.request.query_params

        _all = query_params.get('all')

        data = {}
        data.update(self.get_account_data(_all, query_params))
        data.update(self.get_account_risk_data(_all, query_params))
        data.update(self.get_automation_counts(_all, query_params))

        if _all or query_params.get('total_count_type_to_accounts'):
            data.update({
                'total_count_type_to_accounts': self.get_type_to_accounts(),
            })

        return JsonResponse(data, status=200)

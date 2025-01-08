# -*- coding: utf-8 -*-
#
from django.db.models import Count, F, Q
from django.http.response import JsonResponse
from rest_framework.views import APIView

from accounts.models import Account, RiskChoice
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
        data = {}
        monday_time = local_monday()
        query_params = self.request.query_params

        account_stats = Account.objects.aggregate(
            total_count=Count('id'),
            privileged_count=Count('id', filter=Q(privileged=True)),
            connectivity_ok_count=Count('id', filter=Q(connectivity='ok')),
            secret_reset_count=Count('id', filter=Q(secret_reset=True)),
            unavailable_count=Count('id', filter=Q(is_active=False)),
            week_add_count=Count('id', filter=Q(date_created__gte=monday_time)),
        )

        _all = query_params.get('all')

        if _all or query_params.get('total_accounts'):
            data['total_accounts'] = account_stats['total_count']

        if _all or query_params.get('total_week_add_accounts'):
            data['total_week_add_accounts'] = account_stats['week_add_count']

        if _all or query_params.get('total_privileged_accounts'):
            data['total_privileged_accounts'] = account_stats['privileged_count']

        if _all or query_params.get('total_connectivity_ok_accounts'):
            data['total_connectivity_ok_accounts'] = account_stats['connectivity_ok_count']

        if _all or query_params.get('total_secret_reset_accounts'):
            data['total_secret_reset_accounts'] = account_stats['secret_reset_count']

        if _all or query_params.get('total_ordinary_accounts'):
            data['total_ordinary_accounts'] = account_stats['total_count'] - account_stats['privileged_count']

        if _all or query_params.get('total_unavailable_accounts'):
            data['total_unavailable_accounts'] = account_stats['unavailable_count']

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

        if _all or query_params.get('total_count_type_to_accounts_amount'):
            data.update({
                'total_count_type_to_accounts_amount': self.get_type_to_accounts(),
            })

        return JsonResponse(data, status=200)

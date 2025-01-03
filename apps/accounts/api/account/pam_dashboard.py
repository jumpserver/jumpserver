# -*- coding: utf-8 -*-
#
from django.http.response import JsonResponse
from rest_framework.views import APIView

from accounts.models import Account, RiskChoice

__all__ = ['PamDashboardApi']


class PamDashboardApi(APIView):
    http_method_names = ['get']
    rbac_perms = {
        'GET': 'accounts.view_account',
    }

    def get(self, request, *args, **kwargs):
        query_params = self.request.query_params
        data = {}

        account_count = Account.objects.count()
        privileged_account_count = Account.objects.filter(privileged=True).count()
        
        if query_params.get('total_accounts'):
            data['total_accounts'] = account_count

        if query_params.get('total_privileged_accounts'):
            data['total_privileged_accounts'] = privileged_account_count

        if query_params.get('total_ordinary_accounts'):
            data['total_ordinary_accounts'] = account_count - privileged_account_count

        if query_params.get('total_unmanaged_accounts'):
            data['total_unmanaged_accounts'] = Account.get_risks(RiskChoice.new_found).count()

        if query_params.get('total_unavailable_accounts'):
            data['total_unavailable_accounts'] = Account.objects.filter(is_active=False).count()

        if query_params.get('total_weak_password_accounts'):
            data['total_weak_password_accounts'] = Account.get_risks(RiskChoice.weak_password)

        if query_params.get('total_long_time_change_password_accounts'):
            data['total_long_time_change_password_accounts'] = Account.get_risks(RiskChoice.long_time_password)

        return JsonResponse(data, status=200)

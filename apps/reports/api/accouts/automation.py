# -*- coding: utf-8 -*-
#
from django.http import JsonResponse
from rest_framework.views import APIView

from common.permissions import IsValidLicense
from rbac.permissions import RBACPermission
from reports.mixins import build_account_automation_report, export_table_response

__all__ = ['AccountAutomationApi']


class AccountAutomationApi(APIView):
    http_method_names = ['get']
    rbac_perms = {
        'GET': 'rbac.view_accountautomationreport',
    }
    permission_classes = [RBACPermission, IsValidLicense]

    def get(self, request, *args, **kwargs):
        payload, table, _ = build_account_automation_report(filters={
            'start': request.query_params.get('start'),
            'end': request.query_params.get('end'),
            'range_preset': request.query_params.get('range_preset'),
            'account': request.query_params.get('account', ''),
        }, days=request.query_params.get('days', 7))
        export = request.query_params.get('export')
        if export in ('table', 'csv', 'xlsx'):
            response = export_table_response(table, export)
            if export == 'table':
                return JsonResponse(response, status=200)
            return response
        return JsonResponse(payload, status=200)
# -*- coding: utf-8 -*-
#
from django.http.response import JsonResponse
from rest_framework.views import APIView

from common.permissions import IsValidLicense
from rbac.permissions import RBACPermission
from reports.mixins import build_user_change_password_report, export_table_response

__all__ = ['UserChangeSecretApi']

class UserChangeSecretApi(APIView):
    http_method_names = ['get']
    rbac_perms = {
        'GET': 'rbac.view_userchangepasswordreport',
    }
    permission_classes = [RBACPermission, IsValidLicense]

    def get(self, request, *args, **kwargs):
        payload, table, _ = build_user_change_password_report(filters={
            'start': request.query_params.get('start'),
            'end': request.query_params.get('end'),
            'range_preset': request.query_params.get('range_preset'),
            'user_id': request.query_params.get('user_id', ''),
        }, days=request.query_params.get('days', 7))
        export = request.query_params.get('export')
        if export in ('table', 'csv', 'xlsx'):
            response = export_table_response(table, export)
            if export == 'table':
                return JsonResponse(response, status=200)
            return response
        return JsonResponse(payload, status=200)
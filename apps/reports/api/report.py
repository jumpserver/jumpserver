from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from common.permissions import IsValidLicense
from rbac.permissions import RBACPermission

from reports.mixins import CREATABLE_REPORT_TYPES, build_report_content, export_table_response
from reports.models import (
    Report,
    validate_report_payload,
)
from reports.views import charts_map
from assets.models import Asset

__all__ = ['ReportViewSet']

ALLOWED_REPORT_DAYS = {1, 7, 30}

REPORT_TYPE_ACTION_PERMS = {
    'UserLoginReport': {
        'view': 'rbac.view_userloginreport',
        'create': 'rbac.add_userloginreport',
        'delete': 'rbac.delete_userloginreport',
    },
    'UserChangePasswordReport': {
        'view': 'rbac.view_userchangepasswordreport',
        'create': 'rbac.add_userchangepasswordreport',
        'delete': 'rbac.delete_userchangepasswordreport',
    },
    'AssetStatistics': {
        'view': 'rbac.view_assetstatisticsreport',
        'create': 'rbac.add_assetstatisticsreport',
        'delete': 'rbac.delete_assetstatisticsreport',
    },
    'AssetReport': {
        'view': 'rbac.view_assetactivityreport',
        'create': 'rbac.add_assetactivityreport',
        'delete': 'rbac.delete_assetactivityreport',
    },
    'AccountStatistics': {
        'view': 'rbac.view_accountstatisticsreport',
        'create': 'rbac.add_accountstatisticsreport',
        'delete': 'rbac.delete_accountstatisticsreport',
    },
    'AccountAutomationReport': {
        'view': 'rbac.view_accountautomationreport',
        'create': 'rbac.add_accountautomationreport',
        'delete': 'rbac.delete_accountautomationreport',
    },
}


def get_report_chart_info(report_type):
    chart_info = charts_map.get(report_type, {})
    return {
        'title': str(chart_info.get('title') or report_type),
        'path': chart_info.get('path', ''),
    }


def build_template_item(report_type):
    chart_info = get_report_chart_info(report_type)
    return {
        'tp': report_type,
        'title': chart_info['title'],
        'path': chart_info['path'],
        'is_builtin': True,
        'actions': ['save'],
        'view_modes': ['chart', 'table'],
    }


def serialize_report_summary(report):
    chart_info = get_report_chart_info(report.tp)
    filters = dict(report.filters or {})
    return {
        'id': str(report.id),
        'name': report.name,
        'tp': report.tp,
        'days': report.days,
        'title': chart_info['title'],
        'path': chart_info['path'],
        'filters': filters,
        'is_builtin': report.is_builtin,
        'is_active': report.is_active,
        'actions': ['edit', 'delete'],
        'view_modes': ['chart', 'table'],
    }


class ReportSerializer(serializers.ModelSerializer):
    days = serializers.IntegerField(required=False)
    title = serializers.SerializerMethodField()
    path = serializers.SerializerMethodField()
    supports_table_view = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'name', 'tp', 'is_builtin', 'is_active',
            'days', 'filters',
            'title', 'path', 'supports_table_view', 'actions',
            'date_created', 'date_updated',
        ]
        read_only_fields = [
            'id', 'is_builtin', 'title', 'path', 'supports_table_view', 'actions',
            'date_created', 'date_updated',
        ]

    @staticmethod
    def get_title(obj):
        return get_report_chart_info(obj.tp)['title']

    @staticmethod
    def get_path(obj):
        return get_report_chart_info(obj.tp)['path']

    @staticmethod
    def get_supports_table_view(obj):
        return True

    @staticmethod
    def get_actions(obj):
        return ['edit', 'delete']

    def validate_tp(self, value):
        if value not in CREATABLE_REPORT_TYPES:
            raise serializers.ValidationError('Unsupported report type')
        if self.instance and self.instance.tp != value:
            raise serializers.ValidationError('Report type can not be modified')
        return value

    def validate_days(self, value):
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError('Invalid days')
        if normalized not in ALLOWED_REPORT_DAYS:
            raise serializers.ValidationError('Days must be one of: 1, 7, 30')
        return normalized

    def validate_filters(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('Filters must be a dict')
        validate_report_payload(self.initial_data.get('tp') or getattr(self.instance, 'tp', ''), value)
        if value.get('asset_id') and not Asset.objects.filter(id=str(value.get('asset_id'))).exists():
            raise serializers.ValidationError({'filters': {'asset_id': 'Asset not found'}})
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['filters'] = data.get('filters') or {}
        return data


class ReportViewSet(viewsets.ModelViewSet):
    model = Report
    serializer_class = ReportSerializer
    permission_classes = [RBACPermission, IsValidLicense]
    rbac_perms = {
        'list': 'rbac.view_audit',
        'retrieve': 'rbac.view_audit',
        'create': 'rbac.view_audit',
        'update': 'rbac.view_audit',
        'partial_update': 'rbac.view_audit',
        'destroy': 'rbac.view_audit',
        'templates': 'rbac.view_audit',
        'catalog': 'rbac.view_audit',
        'data': 'rbac.view_audit',
    }

    def get_rbac_perms(self):
        perms = dict(self.rbac_perms)
        action = getattr(self, 'action', None)
        report_type = self._resolve_report_type_for_permission()
        action_perms = REPORT_TYPE_ACTION_PERMS.get(report_type, {}) if isinstance(report_type, str) else {}

        if action in ('retrieve', 'data'):
            if not action_perms.get('view'):
                raise PermissionDenied()
            perms[action] = action_perms['view']
        elif action in ('create', 'update', 'partial_update') and action_perms.get('create'):
            perms[action] = action_perms['create']
        elif action == 'destroy' and action_perms.get('delete'):
            perms[action] = action_perms['delete']

        return perms

    def _resolve_report_type_for_permission(self):
        action = getattr(self, 'action', None)
        if action == 'create':
            return self.request.data.get('tp')

        if action in ('retrieve', 'data', 'update', 'partial_update', 'destroy'):
            lookup_field = self.lookup_field or 'pk'
            lookup_value = self.kwargs.get(lookup_field)
            if lookup_value is None:
                lookup_value = self.kwargs.get('pk')
            if lookup_value:
                return get_object_or_404(self.get_queryset(), pk=lookup_value).tp

        return None

    def get_visible_report_types(self):
        return [
            report_type for report_type in CREATABLE_REPORT_TYPES
            if self.request.user.has_perm(REPORT_TYPE_ACTION_PERMS[report_type]['view'])
        ]

    def get_queryset(self):
        # OrgManager captures the current organization when constructing the query.
        queryset = Report.objects.all().order_by('-date_created')
        if self.action in ('list', 'retrieve', 'data'):
            queryset = queryset.filter(tp__in=self.get_visible_report_types())
        tp = self.request.query_params.get('tp')
        if tp:
            queryset = queryset.filter(tp=tp)
        is_builtin = self.request.query_params.get('is_builtin')
        if is_builtin is not None:
            queryset = queryset.filter(is_builtin=str(is_builtin).lower() in ('1', 'true', 'yes'))
        name = self.request.query_params.get('name')
        if name is not None:
            queryset = queryset.filter(name=name)
        return queryset

    def perform_update(self, serializer):
        if serializer.instance.is_builtin:
            raise serializers.ValidationError({'is_builtin': 'Builtin report template can not be modified'})
        serializer.save()

    def perform_destroy(self, instance):
        if instance.is_builtin:
            raise serializers.ValidationError({'is_builtin': 'Builtin report template can not be deleted'})
        instance.delete()

    @action(methods=['get'], detail=False, url_path='templates')
    def templates(self, request, *args, **kwargs):
        return Response([build_template_item(report_type) for report_type in self.get_visible_report_types()])

    @action(methods=['get'], detail=False, url_path='catalog')
    def catalog(self, request, *args, **kwargs):
        visible_types = self.get_visible_report_types()
        custom_reports = Report.objects.filter(is_builtin=False, tp__in=visible_types).order_by('tp', 'name', '-date_created')
        grouped = {report_type: [] for report_type in visible_types}
        for report in custom_reports:
            if report.tp in grouped:
                grouped[report.tp].append(serialize_report_summary(report))
        data = []
        for report_type in visible_types:
            template = build_template_item(report_type)
            data.append({
                'tp': report_type,
                'title': template['title'],
                'path': template['path'],
                'template': template,
                'children': grouped.get(report_type, []),
            })
        return Response(data)

    @action(methods=['get'], detail=True, url_path='data')
    def data(self, request, *args, **kwargs):
        report = self.get_object()
        filters = dict(report.filters or {})
        days = request.query_params.get('days', 7)
        payload, table, _ = build_report_content(report.tp, filters=filters, days=days)
        export = request.query_params.get('export')
        if export in ('table', 'csv', 'xlsx'):
            response = export_table_response(table, export)
            if export == 'table':
                return Response(response)
            return response
        return Response(payload)

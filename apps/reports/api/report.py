from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsValidLicense
from ops.mixin import PeriodTaskSerializerMixin
from rbac.permissions import RBACPermission

from reports.mixins import CREATABLE_REPORT_TYPES, REPORT_FILTER_FIELDS, build_report_content, export_table_response
from reports.models import (
    Report,
    ReportExecution,
    ReportSendRecord,
    execute_report,
    validate_report_payload,
)
from reports.views import charts_map
from common.serializers.fields import JSONManyToManyField as JSONManyToManySerializerField
from users.models import User
from assets.models import Asset

__all__ = ['ReportViewSet', 'ReportExecutionViewSet', 'ReportSendRecordViewSet']

USER_FILTER_KEY = 'user_id'

REPORT_TYPE_ACTION_PERMS = {
    'UserLoginReport': {
        'create': 'rbac.add_userloginreport',
        'delete': 'rbac.delete_userloginreport',
    },
    'UserChangePasswordReport': {
        'create': 'rbac.add_userchangepasswordreport',
        'delete': 'rbac.delete_userchangepasswordreport',
    },
    'AssetStatistics': {
        'create': 'rbac.add_assetstatisticsreport',
        'delete': 'rbac.delete_assetstatisticsreport',
    },
    'AssetReport': {
        'create': 'rbac.add_assetactivityreport',
        'delete': 'rbac.delete_assetactivityreport',
    },
    'AccountStatistics': {
        'create': 'rbac.add_accountstatisticsreport',
        'delete': 'rbac.delete_accountstatisticsreport',
    },
    'AccountAutomationReport': {
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
        'filters': REPORT_FILTER_FIELDS.get(report_type, []),
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
        'title': chart_info['title'],
        'path': chart_info['path'],
        'filters': filters,
        'filter_fields': REPORT_FILTER_FIELDS.get(report.tp, []),
        'is_builtin': report.is_builtin,
        'is_active': report.is_active,
        'is_periodic': report.is_periodic,
        'periodic_display': report.periodic_display,
        'date_last_run': report.date_last_run,
        'actions': ['edit', 'delete', 'execution_history'],
        'view_modes': ['chart', 'table'],
    }


def merge_report_filters(report, query_params):
    filters = dict(report.filters or {})
    for key in REPORT_FILTER_FIELDS.get(report.tp, []):
        if key not in query_params:
            continue
        value = query_params.get(key)
        if value in (None, ''):
            filters.pop(key, None)
        else:
            filters[key] = value
    return filters


def build_filter_user_options(filters):
    raw = filters.get(USER_FILTER_KEY)
    if not raw:
        return []
    if isinstance(raw, list):
        ids = [str(x) for x in raw if x]
    else:
        ids = [str(raw)]
    users = list(User.objects.filter(id__in=ids))
    return [
        {
            'id': str(u.id),
            'username': u.username,
            'name': (getattr(u, 'name', '') or getattr(u, 'display_name', '') or '')
        }
        for u in users
    ]


class ReportSerializer(PeriodTaskSerializerMixin, serializers.ModelSerializer):
    recipients = JSONManyToManySerializerField(label='Recipients')
    title = serializers.SerializerMethodField()
    path = serializers.SerializerMethodField()
    filter_fields = serializers.SerializerMethodField()
    supports_table_view = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'name', 'tp', 'is_builtin', 'is_active',
            'range_days', 'filters', 'recipients',
            'is_periodic', 'interval', 'crontab',
            'title', 'path', 'filter_fields', 'supports_table_view', 'actions',
            'periodic_display', 'date_last_run', 'date_created', 'date_updated',
        ]
        read_only_fields = [
            'id', 'is_builtin', 'title', 'path', 'filter_fields', 'supports_table_view', 'actions',
            'periodic_display', 'date_last_run', 'date_created', 'date_updated',
        ]

    @staticmethod
    def get_title(obj):
        return get_report_chart_info(obj.tp)['title']

    @staticmethod
    def get_path(obj):
        return get_report_chart_info(obj.tp)['path']

    @staticmethod
    def get_filter_fields(obj):
        return REPORT_FILTER_FIELDS.get(obj.tp, [])

    @staticmethod
    def get_supports_table_view(obj):
        return True

    @staticmethod
    def get_actions(obj):
        return ['edit', 'delete', 'execution_history']

    def validate_tp(self, value):
        if value not in CREATABLE_REPORT_TYPES:
            raise serializers.ValidationError('Unsupported report type')
        if self.instance and self.instance.tp != value:
            raise serializers.ValidationError('Report type can not be modified')
        return value

    def validate_filters(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('Filters must be a dict')
        validate_report_payload(self.initial_data.get('tp') or getattr(self.instance, 'tp', ''), value)
        # Validate asset_id if present: must refer to an existing Asset id
        asset_key = 'asset_id'
        if asset_key in value and value.get(asset_key):
            raw_asset = value.get(asset_key)
            # single value expected
            try:
                asset_id = str(raw_asset)
                if not Asset.objects.filter(id=asset_id).exists():
                    raise serializers.ValidationError({'filters': {asset_key: f'Asset not found: {asset_id}'}})
            except Exception:
                raise serializers.ValidationError({'filters': {asset_key: f'Invalid asset id: {raw_asset}'}})
        # Normalize user filter: accept only user id(s)
        user_key = USER_FILTER_KEY
        if user_key in value and value.get(user_key):
            raw = value.get(user_key)
            # support single value or list
            ids = []
            if isinstance(raw, list):
                str_vals = [str(x) for x in raw if x]
                users = list(User.objects.filter(id__in=str_vals))
                if not users:
                    raise serializers.ValidationError({'filters': {user_key: 'User ids not found'}})
                ids = [str(u.id) for u in users]
            else:
                raw_str = str(raw)
                user = User.objects.filter(id=raw_str).first()
                if not user:
                    raise serializers.ValidationError({'filters': {user_key: f'User id not found: {raw_str}'}})
                ids = [str(user.id)]
            # store single value as string, multiple as list
            value[user_key] = ids[0] if len(ids) == 1 else ids
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        filters = data.get('filters') or {}
        data['filters'] = filters
        # Build filter user options for frontend display
        user_options = build_filter_user_options(filters)
        if user_options:
            data.setdefault('_filter_user_options', {})
            data['_filter_user_options'][USER_FILTER_KEY] = user_options
        return data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        is_periodic = attrs.get('is_periodic', getattr(self.instance, 'is_periodic', False))
        recipients = attrs.get('recipients')
        if recipients is None and self.instance is not None:
            recipients = getattr(self.instance, 'recipients', None)
        if is_periodic and not recipients:
            raise serializers.ValidationError({'recipients': 'Recipients are required for periodic delivery'})
        return attrs


class ReportSendRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSendRecord
        fields = ['id', 'execution', 'backend', 'receiver', 'report_url', 'is_success', 'error', 'detail', 'date_created']
        read_only_fields = fields


class ReportExecutionSerializer(serializers.ModelSerializer):
    send_records = ReportSendRecordSerializer(many=True, read_only=True)
    send_record_count = serializers.IntegerField(source='send_records.count', read_only=True)

    class Meta:
        model = ReportExecution
        fields = [
            'id', 'report', 'status', 'trigger', 'date_created', 'date_start',
            'date_finished', 'duration', 'snapshot', 'summary',
            'send_record_count', 'send_records',
        ]
        read_only_fields = fields


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all().order_by('-date_created')
    serializer_class = ReportSerializer
    permission_classes = [RBACPermission, IsValidLicense]
    rbac_perms = {
        'list': 'rbac.view_audit',
        'retrieve': 'rbac.view_audit',
        'create': 'rbac.view_audit',
        'update': 'rbac.view_audit',
        'partial_update': 'rbac.view_audit',
        'destroy': 'rbac.view_audit',
        'execute': 'rbac.view_audit',
        'templates': 'rbac.view_audit',
        'catalog': 'rbac.view_audit',
        'data': 'rbac.view_audit',
    }

    def get_rbac_perms(self):
        perms = dict(self.rbac_perms)
        action = getattr(self, 'action', None)
        report_type = self._resolve_report_type_for_permission()
        action_perms = REPORT_TYPE_ACTION_PERMS.get(report_type, {}) if isinstance(report_type, str) else {}

        if action in ('create', 'update', 'partial_update') and action_perms.get('create'):
            perms[action] = action_perms['create']
        elif action == 'destroy' and action_perms.get('delete'):
            perms[action] = action_perms['delete']

        return perms

    def _resolve_report_type_for_permission(self):
        action = getattr(self, 'action', None)
        if action == 'create':
            return self.request.data.get('tp')

        if action in ('update', 'partial_update', 'destroy'):
            lookup_field = self.lookup_field or 'pk'
            lookup_value = self.kwargs.get(lookup_field)
            if lookup_value is None:
                lookup_value = self.kwargs.get('pk')
            if lookup_value:
                return Report.objects.filter(pk=lookup_value).values_list('tp', flat=True).first()

        return None

    def get_queryset(self):
        queryset = super().get_queryset()
        tp = self.request.query_params.get('tp')
        if tp:
            queryset = queryset.filter(tp=tp)
        is_builtin = self.request.query_params.get('is_builtin')
        if is_builtin is not None:
            queryset = queryset.filter(is_builtin=str(is_builtin).lower() in ('1', 'true', 'yes'))
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
        return Response([build_template_item(report_type) for report_type in CREATABLE_REPORT_TYPES])

    @action(methods=['get'], detail=False, url_path='catalog')
    def catalog(self, request, *args, **kwargs):
        custom_reports = Report.objects.filter(is_builtin=False).order_by('tp', 'name', '-date_created')
        grouped = {report_type: [] for report_type in CREATABLE_REPORT_TYPES}
        for report in custom_reports:
            if report.tp in grouped:
                grouped[report.tp].append(serialize_report_summary(report))
        data = []
        for report_type in CREATABLE_REPORT_TYPES:
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
        filters = merge_report_filters(report, request.query_params)
        days = request.query_params.get('days', report.range_days)
        payload, table, _ = build_report_content(report.tp, filters=filters, days=days)
        export = request.query_params.get('export')
        if export in ('table', 'csv', 'xlsx'):
            response = export_table_response(table, export)
            if export == 'table':
                return Response(response)
            return response
        return Response(payload)

    @action(methods=['post'], detail=True, url_path='execute')
    def execute(self, request, *args, **kwargs):
        task = execute_report.delay(str(self.get_object().id))
        return Response({'task': str(task.id)}, status=status.HTTP_202_ACCEPTED)

    @action(methods=['get'], detail=True, url_path='executions')
    def executions(self, request, *args, **kwargs):
        queryset = ReportExecution.objects.filter(report=self.get_object()).order_by('-date_start')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReportExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReportExecutionSerializer(queryset, many=True)
        return Response(serializer.data)


class ReportExecutionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = ReportExecution.objects.all().order_by('-date_start')
    serializer_class = ReportExecutionSerializer
    permission_classes = [RBACPermission, IsValidLicense]
    rbac_perms = {'list': 'rbac.view_audit', 'retrieve': 'rbac.view_audit'}

    def get_queryset(self):
        queryset = super().get_queryset()
        report_id = self.request.query_params.get('report')
        if report_id:
            queryset = queryset.filter(report_id=report_id)
        status_value = self.request.query_params.get('status')
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset

    @action(methods=['get'], detail=True, url_path='send-records')
    def send_records(self, request, *args, **kwargs):
        queryset = ReportSendRecord.objects.filter(execution=self.get_object()).order_by('-date_created')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReportSendRecordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReportSendRecordSerializer(queryset, many=True)
        return Response(serializer.data)


class ReportSendRecordViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = ReportSendRecord.objects.all().order_by('-date_created')
    serializer_class = ReportSendRecordSerializer
    permission_classes = [RBACPermission, IsValidLicense]
    rbac_perms = {'list': 'rbac.view_audit', 'retrieve': 'rbac.view_audit'}

    def get_queryset(self):
        queryset = super().get_queryset()
        execution_id = self.request.query_params.get('execution')
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)
        receiver = self.request.query_params.get('receiver')
        if receiver:
            queryset = queryset.filter(receiver=receiver)
        is_success = self.request.query_params.get('is_success')
        if is_success is not None:
            queryset = queryset.filter(is_success=str(is_success).lower() in ('1', 'true', 'yes'))
        return queryset
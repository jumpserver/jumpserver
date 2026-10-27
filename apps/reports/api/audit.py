"""Audit reports: permission-aware previews and reusable layouts."""
import json
import re

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from common.permissions import IsValidLicense, IsValidUser
from orgs.utils import get_current_org
from rbac.permissions import RBACPermission
from reports.audit_contract import (
    CHAPTERS, THEMES, TEMPLATE_TYPES, TYPE_THEMES,
    can_view_theme, can_manage_template,
)
from reports.models import Report
from reports.services.audit_data import generate_report_data
from settings.utils import get_interface_setting_or_default

__all__ = ['AuditReportViewSet', 'AuditReportTemplateViewSet']


class ReportPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100


class ReportConfigSerializer(serializers.Serializer):
    theme = serializers.ChoiceField(choices=tuple(THEMES))
    start = serializers.DateField()
    end = serializers.DateField()
    chapters = serializers.ListField(
        child=serializers.ChoiceField(choices=tuple(CHAPTERS)),
        allow_empty=False, max_length=len(CHAPTERS), required=False,
    )
    title = serializers.CharField(max_length=128, required=False, allow_blank=True, default='')
    header = serializers.CharField(max_length=128, required=False, allow_blank=True, default='')
    conclusion = serializers.CharField(max_length=8000, required=False, allow_blank=True, default='')
    show_logo = serializers.BooleanField(default=True)

    def validate(self, attrs):
        start, end = attrs['start'], attrs['end']
        if start > end:
            raise ValidationError({'end': _('The end date cannot be earlier than the start date.')})
        if (end - start).days + 1 > 366:
            raise ValidationError({'end': _('A report can cover at most 366 days. Select a shorter date range.')})
        if end > timezone.localdate():
            raise ValidationError({'end': _('The end date cannot be later than today. For the current period, report through today.')})
        theme = THEMES[attrs['theme']]
        chapters = attrs.setdefault('chapters', list(theme['chapters']))
        if len(chapters) != len(set(chapters)) or set(chapters) - set(theme['chapters']):
            raise ValidationError({'chapters': _('Chapters are duplicated or do not belong to the selected report theme.')})
        if not set(chapters) & {'overview', 'activity', 'security', 'inventory', 'account'}:
            raise ValidationError({'chapters': _('Select at least one chapter containing statistical data.')})
        attrs['title'] = attrs['title'].strip() or f"{start} — {end} {theme['title']}"
        return attrs


class AuditReportAccessMixin:
    permission_classes = [IsValidUser, RBACPermission, IsValidLicense]
    rbac_perms = {'*': 'rbac.view_audit'}
    pagination_class = ReportPagination

    def require_theme(self, theme):
        if not can_view_theme(self.request.user, theme):
            raise PermissionDenied(_('You do not have permission to view data for this report theme.'))

    @staticmethod
    def require_writable_org():
        org = get_current_org()
        if org.is_root() or org.is_system():
            raise ValidationError(_('Select an organization before saving a template. The all-organizations view supports previews only.'))


def json_value(value):
    return json.loads(JSONRenderer().render(value))


def build_branding(user, generated_at):
    interface = get_interface_setting_or_default()
    variables = {
        'userId': str(user.id), 'name': user.name, 'userName': user.username,
        'currentTime': generated_at,
    }
    template = getattr(settings, 'SECURITY_WATERMARK_CONSOLE_CONTENT', '')
    content = re.sub(r'\$\{(\w+)\}', lambda match: str(variables.get(match[1], '')), template)
    if not content.strip():
        content = f'{get_current_org().name} · {user.username} · {generated_at}'
    return {
        'logo': interface.get('logo_index') or interface.get('logo_logout') or '',
        'generated_by': f'{user.name} ({user.username})',
        'watermark': {
            'content': content,
            'color': getattr(settings, 'SECURITY_WATERMARK_COLOR', 'rgba(184,184,184,0.8)'),
            'font_size': getattr(settings, 'SECURITY_WATERMARK_FONT_SIZE', 13),
            'width': getattr(settings, 'SECURITY_WATERMARK_WIDTH', 200),
            'height': getattr(settings, 'SECURITY_WATERMARK_HEIGHT', 200),
            'rotate': getattr(settings, 'SECURITY_WATERMARK_ROTATE', 45),
        },
    }


def build_snapshot(user, config):
    snapshot = generate_report_data(
        user=user, theme=config['theme'], start=config['start'], end=config['end'], chapters=config['chapters'],
    )
    snapshot['branding'] = build_branding(user, snapshot['generated_at'])
    return json_value(snapshot)


class AuditReportViewSet(AuditReportAccessMixin, viewsets.GenericViewSet):
    serializer_class = ReportConfigSerializer

    @action(detail=False, methods=['get'])
    def catalog(self, request):
        org = get_current_org()
        can_save_template = not (org.is_root() or org.is_system())
        themes = []
        for key, theme in THEMES.items():
            if not can_view_theme(request.user, key):
                continue
            themes.append({
                'key': key, 'title': theme['title'], 'description': theme['description'],
                'chapters': theme['chapters'], 'can_generate': True,
                'can_save_template': can_save_template and can_manage_template(request.user, key),
            })
        return Response({
            'themes': themes,
            'chapters': [{'key': key, 'title': title} for key, title in CHAPTERS.items()],
            'can_save_template': can_save_template, 'max_range_days': 366,
            'organization': {'id': str(org.id), 'name': org.name},
        })

    @action(detail=False, methods=['post'])
    def preview(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config = serializer.validated_data
        self.require_theme(config['theme'])
        return Response(build_snapshot(request.user, config))


class AuditTemplateSerializer(serializers.ModelSerializer):
    theme = serializers.ChoiceField(choices=tuple(THEMES), write_only=True)
    config = serializers.DictField(source='filters')
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ['id', 'name', 'theme', 'config', 'can_edit', 'can_delete', 'created_by', 'date_created', 'date_updated']
        read_only_fields = ['id', 'created_by', 'date_created', 'date_updated']
        # OrgManager determines uniqueness in the current organization.
        validators = []

    def validate(self, attrs):
        theme = attrs.get('theme') or TYPE_THEMES[self.instance.tp]
        if self.instance and TYPE_THEMES[self.instance.tp] != theme:
            raise ValidationError({'theme': _('The report theme of a template cannot be changed. Save a new template instead.')})
        config = attrs.get('filters', getattr(self.instance, 'filters', {}))
        if not isinstance(config, dict):
            raise ValidationError({'config': _('The template configuration must be an object.')})
        if config.get('theme', theme) != theme:
            raise ValidationError({'theme': _('The template theme does not match its configuration.')})
        serializer = ReportConfigSerializer(data={**config, 'theme': theme})
        serializer.is_valid(raise_exception=True)
        # Findings describe a specific period. Reusable layouts must not
        # propagate stale or sensitive manual findings to another report.
        serializer.validated_data['conclusion'] = ''
        user = self.context['request'].user
        if not can_view_theme(user, theme) or not can_manage_template(user, theme):
            raise PermissionDenied(_('You do not have permission to save a template for this report theme.'))
        name = attrs.get('name', getattr(self.instance, 'name', ''))
        duplicates = Report.objects.filter(name=name)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise ValidationError({'name': _('A template with this name already exists in the current organization. Choose another name.')})
        attrs.pop('theme', None)
        attrs.update(tp=TEMPLATE_TYPES[theme], filters=json_value(serializer.validated_data))
        attrs['days'] = (serializer.validated_data['end'] - serializer.validated_data['start']).days + 1
        return attrs

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result['theme'] = TYPE_THEMES[instance.tp]
        return result

    def get_can_edit(self, obj):
        org = get_current_org()
        return not (org.is_root() or org.is_system()) and can_manage_template(
            self.context['request'].user, TYPE_THEMES[obj.tp],
        )

    def get_can_delete(self, obj):
        org = get_current_org()
        return not (org.is_root() or org.is_system()) and can_manage_template(
            self.context['request'].user, TYPE_THEMES[obj.tp], 'delete',
        )


class AuditReportTemplateViewSet(AuditReportAccessMixin, viewsets.ModelViewSet):
    serializer_class = AuditTemplateSerializer

    def get_queryset(self):
        types = [tp for theme, tp in TEMPLATE_TYPES.items() if can_view_theme(self.request.user, theme)]
        queryset = Report.objects.filter(tp__in=types, is_builtin=False).order_by('-date_updated', '-id')
        if theme := self.request.query_params.get('theme'):
            queryset = queryset.filter(tp=TEMPLATE_TYPES.get(theme, ''))
        return queryset

    def perform_create(self, serializer):
        self.require_writable_org()
        try:
            with transaction.atomic():
                serializer.save(created_by=str(self.request.user), updated_by=str(self.request.user))
        except IntegrityError:
            raise ValidationError({'name': _('A template with this name already exists in the current organization. Choose another name.')})

    def perform_update(self, serializer):
        self.require_writable_org()
        try:
            with transaction.atomic():
                serializer.save(updated_by=str(self.request.user))
        except IntegrityError:
            raise ValidationError({'name': _('A template with this name already exists in the current organization. Choose another name.')})

    def perform_destroy(self, instance):
        self.require_writable_org()
        if not can_manage_template(self.request.user, TYPE_THEMES[instance.tp], 'delete'):
            raise PermissionDenied()
        instance.delete()

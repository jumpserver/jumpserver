"""Audit reports: permission-aware previews."""
import json
import re

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from common.permissions import IsValidLicense, IsValidUser
from orgs.utils import get_current_org
from rbac.permissions import RBACPermission
from reports.audit_contract import CHAPTERS, THEMES, can_view_theme
from reports.services.audit_data import generate_report_data
from settings.utils import get_interface_setting_or_default

__all__ = ['AuditReportViewSet']


class ReportConfigSerializer(serializers.Serializer):
    theme = serializers.ChoiceField(choices=tuple(THEMES))
    start = serializers.DateField()
    end = serializers.DateField()
    chapters = serializers.ListField(
        child=serializers.ChoiceField(choices=(*CHAPTERS, 'scope', 'assessment')),
        allow_empty=False, max_length=len(CHAPTERS) + 2, required=False,
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
        if len(chapters) != len(set(chapters)) or set(chapters) - (set(theme['chapters']) | {'scope', 'assessment'}):
            raise ValidationError({'chapters': _('Chapters are duplicated or do not belong to the selected report theme.')})
        # Ignore retired chapters in drafts opened before the catalogue changed.
        chapters = attrs['chapters'] = [chapter for chapter in chapters if chapter not in {'scope', 'assessment'}]
        if not set(chapters) & {'overview', 'activity', 'security', 'inventory', 'account', 'account_health', 'remediation'}:
            raise ValidationError({'chapters': _('Select at least one chapter containing statistical data.')})
        attrs['title'] = attrs['title'].strip() or f"{start} — {end} {theme['title']}"
        return attrs


class AuditReportAccessMixin:
    permission_classes = [IsValidUser, RBACPermission, IsValidLicense]
    rbac_perms = {'*': 'rbac.view_audit'}

    def require_theme(self, theme):
        if not can_view_theme(self.request.user, theme):
            raise PermissionDenied(_('You do not have permission to view data for this report theme.'))



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
        themes = []
        for key, theme in THEMES.items():
            if not can_view_theme(request.user, key):
                continue
            themes.append({
                'key': key, 'title': theme['title'], 'description': theme['description'],
                'chapters': theme['chapters'], 'can_generate': True,
            })
        return Response({
            'themes': themes,
            'chapters': [{'key': key, 'title': title} for key, title in CHAPTERS.items()],
            'max_range_days': 366,
            'organization': {'id': str(org.id), 'name': org.name},
        })

    @action(detail=False, methods=['post'])
    def preview(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config = serializer.validated_data
        self.require_theme(config['theme'])
        return Response(build_snapshot(request.user, config))

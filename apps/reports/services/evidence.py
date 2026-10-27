"""Evidence labels derived from recorded fields, never inferred root causes."""
import uuid

from django.db.models import Case, CharField, Q, Value, When
from django.utils.translation import gettext as _


def reference(value, path='', org_id=''):
    try:
        identifier = str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return _('Not recorded')
    return {'id': identifier, 'label': identifier[:8],
            'path': f'{path}/{identifier}' if path else '', 'org_id': str(org_id)}


def replay_expression():
    return Case(
        When(is_success=False, then=Value('not_applicable')),
        When(has_replay=True, then=Value('recorded')),
        When(error_reason='replay_unsupported', then=Value('unsupported')),
        When(is_finished=False, then=Value('pending')),
        When(error_reason='replay_create_failed', then=Value('create_failed')),
        When(error_reason='replay_upload_failed', then=Value('upload_failed')),
        When(error_reason='replay_convert_failed', then=Value('convert_failed')),
        default=Value('unavailable'), output_field=CharField(),
    )


def replay_labels():
    return {
        'recorded': _('Recording marked present'), 'unsupported': _('Recording unsupported'),
        'pending': _('Session in progress'), 'create_failed': _('Recording creation failed'),
        'upload_failed': _('Recording upload failed'), 'convert_failed': _('Recording conversion failed'),
        'unavailable': _('No recording flag'), 'not_applicable': _('Connection failed; not applicable'),
    }


def connection_reason(row):
    if row['is_success']:
        return '—'
    code = row.get('error_reason', '')
    if code == 'connect_failed':
        return _('Connection failed (no further reason recorded)')
    if not code or code.startswith('replay_'):
        return _('Connection failure reason not recorded')
    return code


def error_category_expression(field='error'):
    # Report categories, never arbitrary error payloads: task errors may contain
    # credentials or connection strings. The original stays in permissioned logs.
    groups = [
        ('authentication', ['authentication failed', 'authentication failure', 'incorrect password', 'invalid password', '认证失败', '密码错误']),
        ('timeout', ['timed out', 'timeout', '超时']),
        ('connection', ['connection refused', 'unreachable', 'no route to host', 'network is unreachable', '无法连接', '连接失败']),
        ('permission', ['permission denied', 'access denied', '权限不足', '权限拒绝']),
        ('missing_target', ['not found', 'does not exist', '不存在']),
        ('verification', ['verify failed', 'verification failed', 'unverified', '验证失败', '未验证']),
    ]
    conditions = [When(Q(**{f'{field}__isnull': True}) | Q(**{field: ''}), then=Value('unrecorded'))]
    for category, patterns in groups:
        condition = Q()
        for pattern in patterns:
            condition |= Q(**{f'{field}__icontains': pattern})
        conditions.append(When(condition, then=Value(category)))
    return Case(*conditions, default=Value('other'), output_field=CharField())


def error_category_labels():
    return {
        'authentication': _('Authentication-related'), 'timeout': _('Execution or connection timeout'),
        'connection': _('Network or connection-related'), 'permission': _('Permission denial-related'),
        'missing_target': _('Target missing or unavailable'), 'verification': _('Result verification-related'),
        'unrecorded': _('Error reason not recorded'), 'other': _('Other error (review the original record)'),
    }

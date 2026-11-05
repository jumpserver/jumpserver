"""Versioned audit projection supplied by Kael in a signed runtime commit."""
import re

from rest_framework.exceptions import ValidationError

from chat_ai.models import AuditConversation, AuditMessage
from orgs.utils import tmp_to_root_org


SECRET_PATTERNS = [
    re.compile(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----', re.I | re.S),
    re.compile(r'\bBearer\s+[A-Za-z0-9._~+/=-]+', re.I),
    re.compile(r'\bsk-[A-Za-z0-9_-]{16,}\b'),
    re.compile(r'\bAKIA[A-Z0-9]{16}\b'),
    re.compile(r'\b(password|passphrase|secret|token|api[ _-]?key|authorization|cookie)\b\s*(?:is|[:=])\s*[^\s,;]+', re.I),
    re.compile(r'(密码|口令|密钥|令牌|私钥)\s*(?:是|为|[:：=])\s*[^\s,，；;]+'),
]


def sanitize_audit_text(value):
    for pattern in SECRET_PATTERNS:
        value = pattern.sub('[REDACTED]', value)
    return value[:32768].strip()


@tmp_to_root_org()
def apply_audit_projection(data, revision):
    """Called under the runtime-store row lock, inside its commit transaction."""
    # A signed Kael commit can contain records from multiple organizations.
    for item in data['conversations']:
        values = dict(item)
        pk = values.pop('id')
        existing = AuditConversation.objects.filter(pk=pk).first()
        if existing and (
            existing.org_id != values['org_id'] or existing.subject_id != values['subject_id']
        ):
            raise ValidationError('An audit conversation cannot change its organization or owner.')
        values['title'] = sanitize_audit_text(values.get('title', ''))
        AuditConversation.objects.update_or_create(pk=pk, defaults={**values, 'source_revision': revision})

    for item in data['messages']:
        values = dict(item)
        pk = values.pop('id')
        conversation = AuditConversation.objects.only('org_id').filter(pk=values['conversation_id']).first()
        if conversation is None:
            raise ValidationError('The audit conversation must be written before its messages.')
        existing = AuditMessage.objects.filter(pk=pk).first()
        if existing and existing.conversation_id != values['conversation_id']:
            raise ValidationError('An audit message cannot change its conversation.')
        values['org_id'] = conversation.org_id
        for field in ('content', 'error'):
            values[field] = sanitize_audit_text(values.get(field, ''))
        AuditMessage.objects.update_or_create(pk=pk, defaults={**values, 'source_revision': revision})

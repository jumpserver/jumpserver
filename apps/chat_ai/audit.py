"""Versioned audit projection supplied by Kael in a signed runtime commit."""
import re

from rest_framework import serializers

from chat_ai.models import AuditConversation, AuditMessage


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


class AuditConversationInput(serializers.ModelSerializer):
    id = serializers.UUIDField()

    class Meta:
        model = AuditConversation
        exclude = ('source_revision',)
        extra_kwargs = {'title': {'allow_blank': True}}


class AuditMessageInput(serializers.ModelSerializer):
    id = serializers.CharField(max_length=128, trim_whitespace=False)
    conversation_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=('user', 'assistant'))

    class Meta:
        model = AuditMessage
        exclude = ('conversation', 'source_revision')


class AuditProjectionInput(serializers.Serializer):
    version = serializers.IntegerField(min_value=1, max_value=1)
    conversations = AuditConversationInput(many=True, required=False, default=list)
    messages = AuditMessageInput(many=True, required=False, default=list)


def apply_audit_projection(data, revision):
    """Called under the runtime-store row lock, inside its commit transaction."""
    for item in data['conversations']:
        values = dict(item)
        pk = values.pop('id')
        existing = AuditConversation.objects.filter(pk=pk).first()
        if existing and (
            existing.org_id != values['org_id'] or existing.subject_id != values['subject_id']
        ):
            raise serializers.ValidationError('An audit conversation cannot change its organization or owner.')
        values['title'] = sanitize_audit_text(values.get('title', ''))
        AuditConversation.objects.update_or_create(pk=pk, defaults={**values, 'source_revision': revision})

    for item in data['messages']:
        values = dict(item)
        pk = values.pop('id')
        if not AuditConversation.objects.filter(pk=values['conversation_id']).exists():
            raise serializers.ValidationError('The audit conversation must be written before its messages.')
        existing = AuditMessage.objects.filter(pk=pk).first()
        if existing and existing.conversation_id != values['conversation_id']:
            raise serializers.ValidationError('An audit message cannot change its conversation.')
        for field in ('content', 'error'):
            values[field] = sanitize_audit_text(values.get(field, ''))
        AuditMessage.objects.update_or_create(pk=pk, defaults={**values, 'source_revision': revision})

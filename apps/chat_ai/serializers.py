import base64
import binascii
import hashlib
import hmac
import json

from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext
from rest_framework import serializers

from .const import JOURNAL_RECORD_FIELDS, MAX_RECORD_BYTES, MAX_REVISION
from .models import AuditConversation, AuditMessage, RuntimeStoreRecord
from .utils import object_without_duplicate_keys


class AuditMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditMessage
        fields = (
            'id', 'role', 'content', 'status', 'error',
            'input_tokens', 'output_tokens', 'date_created',
        )


class AuditConversationSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    message_count = serializers.IntegerField(read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    last_question_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = AuditConversation
        fields = (
            'id', 'title', 'assistant', 'profile', 'status', 'user', 'message_count',
            'question_count', 'last_question_at', 'date_created', 'date_updated',
        )

    @staticmethod
    def get_user(obj):
        return {'id': str(obj.subject_id), 'name': obj.subject_name, 'username': obj.subject_username}


class AuditConversationDetailSerializer(AuditConversationSerializer):
    messages = AuditMessageSerializer(many=True, read_only=True)

    class Meta(AuditConversationSerializer.Meta):
        fields = AuditConversationSerializer.Meta.fields + ('messages',)


class AuditConversationInput(serializers.ModelSerializer):
    id = serializers.UUIDField()
    org_id = serializers.CharField(max_length=36)

    class Meta:
        model = AuditConversation
        fields = (
            'id', 'org_id', 'subject_id', 'subject_name', 'subject_username', 'title',
            'assistant', 'profile', 'status', 'date_created', 'date_updated',
        )
        extra_kwargs = {'title': {'allow_blank': True}}


class AuditMessageInput(serializers.ModelSerializer):
    id = serializers.CharField(max_length=128, trim_whitespace=False)
    conversation_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=('user', 'assistant'))

    class Meta:
        model = AuditMessage
        fields = (
            'id', 'conversation_id', 'role', 'content', 'status', 'error',
            'input_tokens', 'output_tokens', 'date_created',
        )


class AuditProjectionInput(serializers.Serializer):
    version = serializers.IntegerField(min_value=1, max_value=1)
    conversations = AuditConversationInput(many=True, required=False, default=list)
    messages = AuditMessageInput(many=True, required=False, default=list)


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError(gettext('A JSON object is required.'))
        unknown = set(data) - set(self.fields)
        if unknown:
            names = ', '.join(sorted(str(item) for item in unknown))
            raise serializers.ValidationError(gettext('Unknown field(s): %(fields)s.') % {'fields': names})
        return super().to_internal_value(data)


class RuntimeStoreQuerySerializer(StrictSerializer):
    nonce = serializers.UUIDField()
    after = serializers.IntegerField(required=False, default=0, min_value=0, max_value=MAX_REVISION)
    limit = serializers.IntegerField(required=False, default=1000, min_value=1, max_value=1000)


class RuntimeStoreAppendSerializer(StrictSerializer):
    commit_id = serializers.UUIDField()
    expected_revision = serializers.IntegerField(min_value=0, max_value=MAX_REVISION)
    snapshot = serializers.BooleanField()
    record = serializers.CharField(trim_whitespace=False, allow_blank=False)
    integrity = serializers.RegexField(r'^[0-9a-fA-F]{64}$', trim_whitespace=False)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            if 'commit_id' in data and not isinstance(data['commit_id'], str):
                raise serializers.ValidationError({'commit_id': gettext('A UUID string is required.')})
            if isinstance(data.get('expected_revision'), bool):
                raise serializers.ValidationError({
                    'expected_revision': gettext('A non-negative integer is required.')
                })
            if 'snapshot' in data and not isinstance(data['snapshot'], bool):
                raise serializers.ValidationError({'snapshot': gettext('A boolean is required.')})
            if 'record' in data and not isinstance(data['record'], str):
                raise serializers.ValidationError({'record': gettext('A string is required.')})
            if 'integrity' in data and not isinstance(data['integrity'], str):
                raise serializers.ValidationError({'integrity': gettext('A hexadecimal string is required.')})
        return super().to_internal_value(data)

    def validate_record(self, value):
        if len(value.encode('utf-8')) > MAX_RECORD_BYTES:
            raise serializers.ValidationError(gettext('The journal record exceeds the 64 MiB limit.'))

        line = value[:-1] if value.endswith('\n') else value
        if not line or '\n' in line or '\r' in line or line.strip() != line:
            raise serializers.ValidationError(gettext('The journal record must contain exactly one JSON line.'))
        try:
            envelope = json.loads(line, object_pairs_hook=object_without_duplicate_keys)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise serializers.ValidationError(gettext('The journal record is not valid JSON.')) from exc
        allowed_fields = (JOURNAL_RECORD_FIELDS, JOURNAL_RECORD_FIELDS | {'audit'})
        if not isinstance(envelope, dict) or set(envelope) not in allowed_fields:
            raise serializers.ValidationError(
                gettext('The journal record must contain version, created_at, payload, and checksum.')
            )
        version = envelope.get('version')
        if isinstance(version, bool) or version != 1:
            raise serializers.ValidationError(gettext('Unsupported journal record version.'))
        created_at = envelope.get('created_at')
        if (
            not isinstance(created_at, str)
            or len(created_at) > 64
            or parse_datetime(created_at) is None
        ):
            raise serializers.ValidationError(gettext('The journal record created_at is invalid.'))
        payload = envelope.get('payload')
        checksum = envelope.get('checksum')
        if not isinstance(payload, str) or not isinstance(checksum, str) or len(checksum) != 64:
            raise serializers.ValidationError(gettext('The journal record payload or checksum is invalid.'))
        try:
            raw = base64.b64decode(payload, validate=True)
            supplied = bytes.fromhex(checksum)
        except (ValueError, binascii.Error) as exc:
            raise serializers.ValidationError(gettext('The journal record payload or checksum is invalid.')) from exc
        digest = hashlib.sha256(raw).digest()
        if not hmac.compare_digest(digest, supplied):
            raise serializers.ValidationError(gettext('The journal record checksum does not match its payload.'))
        if 'audit' in envelope:
            audit = AuditProjectionInput(data=envelope['audit'])
            audit.is_valid(raise_exception=True)
            self.audit_projection = audit.validated_data
        return value


class RuntimeStoreRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeStoreRecord
        fields = ('revision', 'commit_id', 'snapshot', 'record')
        read_only_fields = fields

import hashlib
import hmac
import json

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.translation import gettext, gettext_lazy
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import APIException, AuthenticationFailed, ParseError
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.backends.drf import SignatureAuthentication
from authentication.models import AccessKey
from common.permissions import IsServiceAccount
from terminal.const import TerminalType

from chat_ai.audit import apply_audit_projection
from chat_ai.const import MAX_RECORD_BYTES
from chat_ai.models import RuntimeStore, RuntimeStoreRecord
from chat_ai.serializers import (
    RuntimeStoreAppendSerializer, RuntimeStoreQuerySerializer, RuntimeStoreRecordSerializer,
)
from chat_ai.utils import object_without_duplicate_keys


RUNTIME_STORE_KEY = 'default'
MAX_REQUEST_BYTES = MAX_RECORD_BYTES + 8192
MAX_PAGE_RECORD_BYTES = 64 * 1024 * 1024
COMMIT_INTEGRITY_PURPOSE = 'kael-runtime-store-commit-v1'
COMMIT_RECEIPT_PURPOSE = 'kael-runtime-store-receipt-v1'
PAGE_RECEIPT_PURPOSE = 'kael-runtime-store-page-v1'


class RuntimeStorePayloadTooLarge(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = gettext_lazy('The runtime store request exceeds the 64 MiB record limit.')
    default_code = 'runtime_store_payload_too_large'


class RuntimeStoreJSONParser(JSONParser):
    """Bound the actual stream size, including requests without Content-Length."""

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', 'utf-8')
        raw = stream.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise RuntimeStorePayloadTooLarge()
        try:
            return json.loads(
                raw.decode(encoding),
                object_pairs_hook=object_without_duplicate_keys,
            )
        except (UnicodeDecodeError, ValueError) as exc:
            raise ParseError(gettext('JSON parse error - %(error)s') % {'error': exc}) from exc


class IsKaelTerminal(permissions.BasePermission):
    message = gettext_lazy('Only a Kael terminal service account may access the runtime store.')

    def has_permission(self, request, view):
        try:
            terminal = request.user.terminal
        except (AttributeError, ObjectDoesNotExist):
            return False
        return terminal.type == TerminalType.kael


def _snapshot_bit(snapshot):
    return '1' if snapshot else '0'


def _record_hash(record):
    return hashlib.sha256(record.encode('utf-8')).hexdigest()


def _sign(secret, parts):
    message = '\n'.join(str(item) for item in parts).encode('utf-8')
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _commit_integrity(secret, commit_id, expected_revision, snapshot, record_hash):
    return _sign(secret, (
        COMMIT_INTEGRITY_PURPOSE,
        RUNTIME_STORE_KEY,
        commit_id,
        expected_revision,
        _snapshot_bit(snapshot),
        record_hash,
    ))


def _commit_receipt(
    secret, commit_id, expected_revision, revision, snapshot, record_hash,
):
    return _sign(secret, (
        COMMIT_RECEIPT_PURPOSE,
        RUNTIME_STORE_KEY,
        commit_id,
        expected_revision,
        revision,
        _snapshot_bit(snapshot),
        record_hash,
    ))


def _page_receipt(secret, nonce, after, limit, revision, has_more, rows):
    parts = [
        PAGE_RECEIPT_PURPOSE,
        RUNTIME_STORE_KEY,
        nonce,
        after,
        limit,
        revision,
        _snapshot_bit(has_more),
        len(rows),
    ]
    for row in rows:
        parts.extend((
            row.revision,
            row.commit_id,
            _snapshot_bit(row.snapshot),
            _record_hash(row.record),
        ))
    return _sign(secret, parts)


def _request_access_key_secret(request):
    access_key = AccessKey.objects.select_related('user').filter(
        pk=request.auth,
        user_id=request.user.pk,
    ).first()
    if not access_key or not access_key.is_valid:
        raise AuthenticationFailed(gettext('Invalid runtime store access key.'))
    return str(access_key.secret).encode('utf-8')


def _locked_runtime_store():
    store, _ = RuntimeStore.objects.get_or_create(key=RUNTIME_STORE_KEY)
    return RuntimeStore.objects.select_for_update().get(pk=store.pk)


class RuntimeStoreView(APIView):
    """Durable, globally ordered runtime journal used only by Kael."""

    authentication_classes = (SignatureAuthentication,)
    permission_classes = (IsServiceAccount, IsKaelTerminal)
    parser_classes = (RuntimeStoreJSONParser,)
    schema = None

    @extend_schema(exclude=True)
    def get(self, request):
        query = RuntimeStoreQuerySerializer(data=request.query_params.dict())
        query.is_valid(raise_exception=True)
        nonce = query.validated_data['nonce']
        after = query.validated_data['after']
        limit = query.validated_data['limit']
        secret = _request_access_key_secret(request)

        with transaction.atomic():
            store = _locked_runtime_store()
            revision = store.revision
            records = store.records.filter(revision__lte=revision)
            if store.snapshot_revision and after < store.snapshot_revision:
                records = records.filter(revision__gte=store.snapshot_revision)
            else:
                records = records.filter(revision__gt=after)
            rows = []
            page_record_bytes = 0
            has_more = False
            for record in records.order_by('revision').iterator(chunk_size=10):
                record_bytes = len(record.record.encode('utf-8'))
                if len(rows) >= limit or (
                    rows and page_record_bytes + record_bytes > MAX_PAGE_RECORD_BYTES
                ):
                    has_more = True
                    break
                rows.append(record)
                page_record_bytes += record_bytes

        receipt = _page_receipt(
            secret, nonce, after, limit, revision, has_more, rows,
        )

        response = Response({
            'nonce': str(nonce),
            'revision': revision,
            'results': RuntimeStoreRecordSerializer(rows, many=True).data,
            'has_more': has_more,
            'receipt': receipt,
        })
        response['Cache-Control'] = 'no-store'
        return response

    @extend_schema(exclude=True)
    def post(self, request):
        serializer = RuntimeStoreAppendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        commit_id = serializer.validated_data['commit_id']
        expected_revision = serializer.validated_data['expected_revision']
        is_snapshot = serializer.validated_data['snapshot']
        record = serializer.validated_data['record']
        record_hash = _record_hash(record)
        secret = _request_access_key_secret(request)
        expected_integrity = _commit_integrity(
            secret, commit_id, expected_revision, is_snapshot, record_hash,
        )
        if not hmac.compare_digest(
            expected_integrity, serializer.validated_data['integrity'].lower(),
        ):
            raise AuthenticationFailed(gettext('Invalid runtime store commit integrity.'))

        with transaction.atomic():
            store = _locked_runtime_store()
            existing = RuntimeStoreRecord.objects.filter(commit_id=commit_id).first()
            if existing:
                identical_retry = (
                    existing.store_id == store.id
                    and existing.revision == expected_revision + 1
                    and existing.snapshot == is_snapshot
                    and existing.record == record
                    and store.revision == existing.revision
                )
                if not identical_retry:
                    return self._revision_conflict(store.revision)
                revision = existing.revision
            elif store.revision != expected_revision:
                return self._revision_conflict(store.revision)
            else:
                revision = store.revision + 1
                audit = getattr(serializer, 'audit_projection', None)
                if audit is not None:
                    apply_audit_projection(audit, revision)
                RuntimeStoreRecord.objects.create(
                    store=store,
                    revision=revision,
                    commit_id=commit_id,
                    snapshot=is_snapshot,
                    record=record,
                )
                if is_snapshot:
                    store.records.filter(revision__lt=revision).delete()
                    store.snapshot_revision = revision
                store.revision = revision
                store.save(update_fields=('revision', 'snapshot_revision', 'date_updated'))

        receipt = _commit_receipt(
            secret, commit_id, expected_revision, revision, is_snapshot, record_hash,
        )
        return Response(
            {
                'revision': revision,
                'commit_id': str(commit_id),
                'receipt': receipt,
                'audit_version': 1,
            },
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _revision_conflict(current_revision):
        return Response(
            {
                'code': 'runtime_store_revision_conflict',
                'detail': gettext('The runtime store revision has changed.'),
                'current_revision': current_revision,
            },
            status=status.HTTP_409_CONFLICT,
        )

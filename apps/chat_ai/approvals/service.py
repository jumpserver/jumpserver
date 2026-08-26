import hashlib
import hmac
import json
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from chat_ai.executor.request_builder import RequestBuilder
from chat_ai.executor.sanitizer import summarize
from chat_ai.models import AgentRun, Approval, Message
from chat_ai.policies import PolicyEngine
from chat_ai.signing import SigningKeyUnavailable, get_signing_key


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str)


class ApprovalService:
    def __init__(self, registry, policy=None):
        self.registry = registry
        self.policy = policy or PolicyEngine()
        self.builder = RequestBuilder()

    @staticmethod
    def request_hash(payload):
        return hashlib.sha256(canonical_json(payload).encode()).hexdigest()

    @staticmethod
    def signature_payload(approval):
        return {
            'approval_id': str(approval.id),
            'user_id': str(approval.user_id),
            'org_id': str(approval.org_id),
            'conversation_id': str(approval.conversation_id or ''),
            'operation_id': approval.operation_id,
            'method': approval.method,
            'path': approval.path,
            'risk_level': approval.risk_level,
            'expires_at': int(approval.expires_at.timestamp()),
            'nonce': approval.nonce,
            'signing_key_id': approval.signing_key_id,
            'request_hash': approval.request_hash,
        }

    @classmethod
    def signature_for(cls, approval):
        key = get_signing_key(
            key_id=approval.signing_key_id,
            key_id_setting='CHAT_AI_APPROVAL_KEY_ID',
            secret_setting='CHAT_AI_APPROVAL_SECRET',
            verify_keys_setting='CHAT_AI_APPROVAL_VERIFY_KEYS',
            purpose='jumpserver-chat-ai-approval-v1',
        )
        value = canonical_json(cls.signature_payload(approval)).encode()
        return hmac.new(key, value, hashlib.sha256).hexdigest()

    def create(self, *, conversation, agent_run, user, org_id, operation, arguments):
        decision = self.policy.enforce(operation, arguments)
        if not decision.requires_approval:
            raise ValidationError('This operation does not require approval.')
        path, query_params, body = self.builder.build(operation, arguments)
        payload = {
            'path_params': arguments.get('path_params') or {},
            'query_params': query_params,
            'body': body,
        }
        approval = Approval.objects.create(
            conversation=conversation,
            agent_run=agent_run,
            user=user,
            org_id=str(org_id),
            operation_id=operation.operation_id,
            method=operation.method,
            path=path,
            request_payload=payload,
            request_hash=self.request_hash(payload),
            nonce=uuid.uuid4().hex,
            signing_key_id=str(getattr(settings, 'CHAT_AI_APPROVAL_KEY_ID', 'v1') or 'v1'),
            signature='',
            risk_level=decision.risk_level,
            expires_at=timezone.now() + timedelta(seconds=getattr(settings, 'CHAT_AI_APPROVAL_TTL', 600)),
        )
        approval.signature = self.signature_for(approval)
        approval.save(update_fields=('signature', 'date_updated'))
        return approval

    def prepare_confirmation(self, approval_id, user, org_id):
        with transaction.atomic():
            approval = Approval.objects.select_for_update().get(pk=approval_id)
            if approval.user_id != user.id:
                raise PermissionDenied('Approval belongs to another user.')
            if str(approval.org_id) != str(org_id):
                raise PermissionDenied('Approval belongs to another organization.')
            if approval.status != Approval.Status.PENDING:
                raise ValidationError(f'Approval is already {approval.status}.')
            if approval.expires_at <= timezone.now():
                approval.status = Approval.Status.EXPIRED
                approval.save(update_fields=('status', 'date_updated'))
                if approval.agent_run:
                    approval.agent_run.status = AgentRun.Status.FAILED
                    approval.agent_run.finished_at = timezone.now()
                    approval.agent_run.error = 'APPROVAL_EXPIRED'
                    approval.agent_run.save(update_fields=('status', 'finished_at', 'error', 'date_updated'))
                    if approval.agent_run.assistant_message:
                        approval.agent_run.assistant_message.status = Message.Status.FAILED
                        approval.agent_run.assistant_message.error = 'APPROVAL_EXPIRED'
                        approval.agent_run.assistant_message.save(update_fields=('status', 'error', 'date_updated'))
                raise ValidationError('Approval has expired.')
            if not hmac.compare_digest(approval.request_hash, self.request_hash(approval.request_payload)):
                raise PermissionDenied('Approval request hash is invalid.')
            try:
                expected_signature = self.signature_for(approval)
            except SigningKeyUnavailable as exc:
                raise PermissionDenied('Approval signing key is unavailable.') from exc
            if not hmac.compare_digest(approval.signature, expected_signature):
                raise PermissionDenied('Approval signature is invalid.')

            operation = self.registry.get(approval.operation_id)
            if not operation or operation.method != approval.method:
                raise PermissionDenied('Approved operation no longer exists.')
            self.policy.enforce(operation, approval.request_payload)
            path, _, _ = self.builder.build(operation, approval.request_payload)
            if path != approval.path:
                raise PermissionDenied('Approved operation path has changed.')
            approval.status = Approval.Status.PROCESSING
            approval.confirmed_by = user
            approval.confirmed_at = timezone.now()
            approval.expires_at = timezone.now() + timedelta(
                seconds=getattr(settings, 'CHAT_AI_API_TIMEOUT', 15) + 60
            )
            approval.save(update_fields=(
                'status', 'confirmed_by', 'confirmed_at', 'expires_at', 'date_updated'
            ))
        return approval, operation

    @staticmethod
    def finish(approval, result):
        ok = bool(result.get('ok'))
        approval.status = Approval.Status.CONFIRMED if ok else Approval.Status.FAILED
        approval.result_summary = summarize(result)
        approval.error = '' if ok else f'Core API returned HTTP {result.get("status_code", 0)}'
        approval.save(update_fields=('status', 'result_summary', 'error', 'date_updated'))
        run = approval.agent_run
        message = None
        if run:
            run.status = AgentRun.Status.COMPLETED if ok else AgentRun.Status.FAILED
            run.finished_at = timezone.now()
            run.error = approval.error
            run.save(update_fields=('status', 'finished_at', 'error', 'date_updated'))
            message = run.assistant_message
        result_text = (
            f'Operation {approval.operation_id} completed successfully.' if ok
            else f'Operation {approval.operation_id} failed with HTTP {result.get("status_code", 0)}.'
        )
        if approval.conversation:
            Message.objects.create(
                conversation=approval.conversation,
                role=Message.Role.TOOL,
                status=Message.Status.COMPLETED,
                content=json.dumps(summarize({
                    'operation_id': approval.operation_id,
                    'result': result,
                }), ensure_ascii=False),
                model=message.model if message else '',
            )
        if message:
            message.status = Message.Status.COMPLETED if ok else Message.Status.FAILED
            message.content = '\n\n'.join(item for item in (message.content, result_text) if item)
            message.error = approval.error
            message.save(update_fields=('status', 'content', 'error', 'date_updated'))
        elif approval.conversation:
            Message.objects.create(
                conversation=approval.conversation,
                role=Message.Role.ASSISTANT,
                status=Message.Status.COMPLETED if ok else Message.Status.FAILED,
                content=result_text,
            )

    @staticmethod
    def fail(approval, error):
        error_code = error.__class__.__name__
        approval.status = Approval.Status.FAILED
        approval.error = error_code
        approval.save(update_fields=('status', 'error', 'date_updated'))
        if approval.agent_run:
            approval.agent_run.status = AgentRun.Status.FAILED
            approval.agent_run.finished_at = timezone.now()
            approval.agent_run.error = error_code
            approval.agent_run.save(update_fields=('status', 'finished_at', 'error', 'date_updated'))
            if approval.agent_run.assistant_message:
                approval.agent_run.assistant_message.status = Message.Status.FAILED
                approval.agent_run.assistant_message.error = error_code
                approval.agent_run.assistant_message.save(
                    update_fields=('status', 'error', 'date_updated')
                )

    @staticmethod
    def cancel(approval_id, user, org_id):
        with transaction.atomic():
            approval = Approval.objects.select_for_update().get(pk=approval_id)
            if approval.user_id != user.id or str(approval.org_id) != str(org_id):
                raise PermissionDenied('Approval is not accessible.')
            if approval.status != Approval.Status.PENDING:
                raise ValidationError(f'Approval is already {approval.status}.')
            approval.status = Approval.Status.CANCELLED
            approval.save(update_fields=('status', 'date_updated'))
            if approval.agent_run:
                approval.agent_run.status = AgentRun.Status.CANCELLED
                approval.agent_run.finished_at = timezone.now()
                approval.agent_run.save(update_fields=('status', 'finished_at', 'date_updated'))
                if approval.agent_run.assistant_message:
                    approval.agent_run.assistant_message.status = Message.Status.CANCELLED
                    approval.agent_run.assistant_message.save(update_fields=('status', 'date_updated'))
            return approval

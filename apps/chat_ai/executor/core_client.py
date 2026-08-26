import asyncio
import json
import time

import httpx
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db.models import F

from common.utils import get_logger

from chat_ai.models import AgentRun, ApiCallAudit
from chat_ai.policies import PolicyEngine
from chat_ai.presentation import build_result_card
from chat_ai.delegation import (
    HEADER_NAME, OPERATION_HEADER_NAME, issue_delegation,
    request_binding_hash,
)

from .request_builder import RequestBuilder
from .sanitizer import sanitize_text, summarize


logger = get_logger(__name__)


class CoreAPIExecutor:
    def __init__(self, registry, policy=None):
        self.registry = registry
        self.policy = policy or PolicyEngine()
        self.builder = RequestBuilder()

    async def _audit(self, *, agent_run, operation, path, request_summary, response_summary=None,
                     status_code=0, duration_ms=0, error='', approval=None, risk_level=''):
        await sync_to_async(ApiCallAudit.objects.create, thread_sensitive=True)(
            agent_run=agent_run,
            conversation_id=agent_run.conversation_id if agent_run else approval.conversation_id,
            message_id=agent_run.assistant_message_id if agent_run else None,
            approval_id=approval.id if approval else None,
            user_id=agent_run.user_id if agent_run else approval.user_id,
            org_id=str(agent_run.org_id if agent_run else approval.org_id),
            operation_id=operation.operation_id,
            method=operation.method,
            path=path,
            request_summary=summarize(request_summary),
            response_summary=summarize(response_summary or {}),
            status_code=status_code,
            risk_level=risk_level or operation.risk_level,
            duration_ms=duration_ms,
            error=sanitize_text(error)[:1024],
        )
        if agent_run:
            await sync_to_async(AgentRun.objects.filter(pk=agent_run.pk).update, thread_sensitive=True)(
                api_call_count=F('api_call_count') + 1
            )

    async def execute(self, operation_id, arguments, auth_context, agent_run=None, approval=None):
        if not agent_run and not approval:
            raise ValueError('A trusted AgentRun or Approval context is required.')
        operation = self.registry.get(operation_id)
        if not operation:
            raise ValueError('Unknown Core API operation.')
        decision = self.policy.enforce(operation, arguments)
        path, query_params, body = self.builder.build(operation, arguments)
        serialized_query = self.builder.serialize_query(operation, query_params)
        request_summary = {
            'path_params': arguments.get('path_params') or {},
            'query_params': query_params,
            'body': body,
        }
        started = time.monotonic()
        status_code = 0
        try:
            base_url = getattr(settings, 'CHAT_AI_CORE_BASE_URL', 'http://127.0.0.1:8080').rstrip('/')
            timeout = getattr(settings, 'CHAT_AI_API_TIMEOUT', 15)
            max_bytes = getattr(settings, 'CHAT_AI_MAX_RESPONSE_BYTES', 1024 * 1024)
            verify = getattr(settings, 'CHAT_AI_CORE_TLS_VERIFY', True)
            ca_cert = getattr(settings, 'CHAT_AI_CORE_CA_CERT', '') or ''
            if ca_cert:
                verify = ca_cert
            client_cert = getattr(settings, 'CHAT_AI_CORE_CLIENT_CERT', '') or ''
            client_key = getattr(settings, 'CHAT_AI_CORE_CLIENT_KEY', '') or ''
            cert = (client_cert, client_key) if client_key else (client_cert or None)
            async with asyncio.timeout(timeout):
                async with httpx.AsyncClient(
                    base_url=base_url,
                    timeout=timeout,
                    follow_redirects=False,
                    verify=verify,
                    cert=cert,
                    trust_env=False,
                ) as client:
                    headers = auth_context.headers()
                    headers[OPERATION_HEADER_NAME] = operation.operation_id
                    request_kwargs = {
                        'method': operation.method,
                        'url': path,
                        'params': serialized_query,
                        'headers': headers,
                    }
                    if operation.method != 'GET' and operation.request_body_schema:
                        request_kwargs['json'] = body
                    request = client.build_request(**request_kwargs)
                    request_hash = request_binding_hash(
                        operation.method,
                        path,
                        request.url.query,
                        request.content,
                    )
                    request.headers[HEADER_NAME] = issue_delegation(
                        user_id=auth_context.user_id,
                        org_id=auth_context.org_id,
                        conversation_id=agent_run.conversation_id if agent_run else approval.conversation_id,
                        approval_id=approval.id if approval else '',
                        operation_id=operation.operation_id,
                        method=operation.method,
                        path=path,
                        request_hash=request_hash,
                        ttl=min(timeout + 5, 60),
                    )
                    response = await client.send(request, stream=True)
                    try:
                        status_code = response.status_code
                        chunks = bytearray()
                        async for chunk in response.aiter_bytes():
                            chunks.extend(chunk)
                            if len(chunks) > max_bytes:
                                raise ValueError('Core API response exceeded the configured size limit.')
                        raw = bytes(chunks)
                        try:
                            data = json.loads(raw.decode('utf-8')) if raw else None
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            data = raw.decode('utf-8', errors='replace')
                    finally:
                        await response.aclose()
            duration_ms = int((time.monotonic() - started) * 1000)
            result = {
                'ok': 200 <= status_code < 300,
                'status_code': status_code,
                'operation_id': operation.operation_id,
                'data': summarize(data),
            }
            try:
                result['presentation'] = build_result_card(operation, result)
            except Exception:
                logger.warning(
                    'Chat AI result card could not be built for operation %s.',
                    operation.operation_id,
                )
                result['presentation'] = None
            await self._audit(
                agent_run=agent_run, operation=operation, path=path,
                request_summary=request_summary, response_summary=data,
                status_code=status_code, duration_ms=duration_ms,
                approval=approval,
                risk_level=decision.risk_level,
            )
            return result
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            await self._audit(
                agent_run=agent_run, operation=operation, path=path,
                request_summary=request_summary, status_code=status_code,
                duration_ms=duration_ms, error=exc.__class__.__name__,
                approval=approval,
                risk_level=decision.risk_level,
            )
            raise

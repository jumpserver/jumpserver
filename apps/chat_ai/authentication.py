import hmac

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import authentication, exceptions

from .delegation import (
    HEADER_NAME, OPERATION_HEADER_NAME, request_binding_hash,
    verify_delegation,
)


class ChatAIDelegationAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        token = request.headers.get(HEADER_NAME)
        if not token:
            return None
        payload = verify_delegation(token)
        if not payload:
            raise exceptions.AuthenticationFailed('Invalid Chat AI delegation credential.')
        operation_id = request.headers.get(OPERATION_HEADER_NAME, '')
        org_id = request.headers.get('X-JMS-ORG', '')
        if operation_id != payload['allowed_operation_id']:
            raise exceptions.AuthenticationFailed('Chat AI delegation operation mismatch.')
        if str(org_id) != str(payload['org_id']):
            raise exceptions.AuthenticationFailed('Chat AI delegation organization mismatch.')
        current_org = getattr(request._request, 'current_org', None)
        if not current_org or str(current_org.id) != str(payload['org_id']):
            raise exceptions.AuthenticationFailed('Chat AI delegation organization context mismatch.')
        if request.method.upper() != payload['method'] or request.path_info != payload['path']:
            raise exceptions.AuthenticationFailed('Chat AI delegation request mismatch.')
        try:
            request_hash = request_binding_hash(
                request.method,
                payload['path'],
                request.META.get('QUERY_STRING', ''),
                request._request.body,
            )
        except Exception as exc:
            raise exceptions.AuthenticationFailed('Chat AI delegation request could not be verified.') from exc
        if not hmac.compare_digest(request_hash, payload['request_hash']):
            raise exceptions.AuthenticationFailed('Chat AI delegation request body mismatch.')
        nonce_key = f'chat-ai:delegation-used:{payload["nonce"]}'
        try:
            nonce_is_new = cache.add(nonce_key, True, timeout=60)
        except Exception as exc:
            raise exceptions.AuthenticationFailed('Chat AI delegation replay protection is unavailable.') from exc
        if not nonce_is_new:
            raise exceptions.AuthenticationFailed('Chat AI delegation credential was already used.')
        user = get_user_model().objects.filter(id=payload['user_id']).first()
        if not user or not user.is_active or not user.is_valid:
            raise exceptions.AuthenticationFailed('Chat AI delegation user is invalid.')
        return user, payload

    def authenticate_header(self, request):
        return 'JMS-AI-Delegation'

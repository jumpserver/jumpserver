import hashlib
import json
import math
from datetime import datetime

from django.utils import timezone
from oauth2_provider.models import get_access_token_model, get_refresh_token_model
from oauth2_provider.oauth2_validators import OAuth2Validator
from oauthlib.oauth2 import InvalidGrantError, InvalidRequestError

from authentication.models.client_login_session import ClientLoginSession
from authentication.services.client_login_session import (
    CLIENT_ACCESS_TOKEN_EXPIRE_SECONDS, client_login_lifetime, client_login_policy, client_login_session_data, client_session_deadline,
    is_client_application, revoke_session, validate_refresh_token_session, client_session_receipt,
)


AUTHENTICATED_AT_CLAIM = '_jumpserver_client_authenticated_at'


class ClientSessionInvalidGrant(InvalidGrantError):
    def __init__(self, session):
        super().__init__(description='Client login session expired.')
        self.session = session

    @property
    def twotuples(self):
        return [*super().twotuples,
                ('client_login_reason', self.session.client_login_reason),
                ('client_login_session', client_login_session_data(self.session))]


class ClientOAuth2Validator(OAuth2Validator):
    def _save_bearer_token(self, token, request, *args, **kwargs):
        if not is_client_application(request.client):
            return super()._save_bearer_token(token, request, *args, **kwargs)

        token['expires_in'] = CLIENT_ACCESS_TOKEN_EXPIRE_SECONDS
        authenticated_at = getattr(request, 'client_authenticated_at', None)
        refresh = getattr(request, 'refresh_token_instance', None)
        session = getattr(refresh, 'client_login_session', None)
        if refresh is not None:
            if session is None:
                session = ClientLoginSession.objects.filter(
                    application=request.client, token_family=refresh.token_family,
                ).first()
            authenticated_at = session.authenticated_at if session else None
        policy = getattr(session, 'client_login_policy', None) or client_login_policy()
        lifetime = client_login_lifetime(policy)
        # The original lifetime stays fixed. A policy change has its own earlier
        # exit deadline; token rotation must respect both without changing either.
        expires_at = client_session_deadline(session)[0] if session else None
        if lifetime and session is None:
            if authenticated_at is None:
                raise InvalidGrantError(description='Client login authorization is required.')
            expires_at = authenticated_at + lifetime
        if expires_at and timezone.now() >= expires_at:
            raise InvalidGrantError(description='Client login session expired.')
        request.client_login_expires_at = expires_at

        result = super()._save_bearer_token(token, request, *args, **kwargs)
        access = get_access_token_model().objects.get(
            application=request.client,
            token_checksum=hashlib.sha256(token['access_token'].encode('utf-8')).hexdigest(),
        )
        if expires_at:
            remaining = (expires_at - timezone.now()).total_seconds()
            if remaining <= 0:
                # save_bearer_token's transaction rolls back issuance at the boundary.
                raise InvalidGrantError(description='Client login session expired.')
            # Also covers non-rotating refresh and grace-period retries. The DB
            # keeps the exact deadline; OAuth's expires_in has whole-second precision.
            if access.expires > expires_at:
                access.expires = expires_at
                access.save(update_fields=('expires',))
            token['refresh_token_expires_in'] = math.ceil(remaining)
        else:
            token['refresh_token_expires_in'] = 0
        # Grace retries may return an existing token even for an unlimited login.
        token['expires_in'] = max(0, math.ceil((access.expires - timezone.now()).total_seconds()))
        token['client_login_expires_at'] = expires_at.isoformat() if expires_at else None
        # Return the policy used by this actual, serialized token issuance.
        token['client_login_policy'] = policy
        session = session or request.client_login_session
        token['client_login_session'] = client_login_session_data(session)
        token['client_login_session_receipt'] = client_session_receipt(
            request.client.pk, session.token_family, token,
        )
        return result

    def _create_authorization_code(self, request, code, expires=None):
        claims = request.claims
        if claims is None or claims == '':
            claims = {}
        elif isinstance(claims, str):
            try:
                claims = json.loads(claims)
            except (TypeError, ValueError):
                raise InvalidRequestError(description='Invalid authorization claims.', request=request)
        if not isinstance(claims, dict):
            raise InvalidRequestError(description='Authorization claims must be a JSON object.', request=request)
        claims = dict(claims)
        claims.pop(AUTHENTICATED_AT_CLAIM, None)
        request.claims = claims
        if is_client_application(request.client):
            # The existing Web login authorizes a new client login session.
            # Ignore caller-supplied timestamps and start its clock here;
            # refresh token rotation never replaces this authorization time.
            claims[AUTHENTICATED_AT_CLAIM] = timezone.now().isoformat()
        return super()._create_authorization_code(request, code, expires)

    def validate_code(self, client_id, code, client, request, *args, **kwargs):
        if not super().validate_code(client_id, code, client, request, *args, **kwargs):
            return False
        if is_client_application(client):
            try:
                authenticated_at = datetime.fromisoformat(request.claims[AUTHENTICATED_AT_CLAIM])
                if timezone.is_naive(authenticated_at) or authenticated_at > timezone.now():
                    return False
                request.client_authenticated_at = authenticated_at
            except (AttributeError, KeyError, TypeError, ValueError):
                return False
        return True

    def validate_refresh_token(self, refresh_token, client, request, *args, **kwargs):
        if not super().validate_refresh_token(refresh_token, client, request, *args, **kwargs):
            return False
        refresh = request.refresh_token_instance
        valid = validate_refresh_token_session(refresh)
        session = getattr(refresh, 'client_login_session', None)
        if not valid and session and session.client_login_reason:
            # The valid credential already identified its session. Reuse it for
            # the error detail instead of resolving the receipt a second time.
            raise ClientSessionInvalidGrant(session)
        return valid

    def _create_refresh_token(self, request, refresh_token_code, access_token, previous_refresh_token):
        refresh = super()._create_refresh_token(request, refresh_token_code, access_token, previous_refresh_token)
        if previous_refresh_token is None and is_client_application(request.client):
            authenticated_at = getattr(request, 'client_authenticated_at', None)
            if authenticated_at is None:
                raise InvalidGrantError(description='Client login authorization is required.')
            request.client_login_session = ClientLoginSession.objects.create(
                user=request.user, application=request.client, token_family=refresh.token_family,
                authenticated_at=authenticated_at,
                expires_at=request.client_login_expires_at,
            )
        return refresh

    def revoke_token(self, token, token_type_hint, request, *args, **kwargs):
        if is_client_application(request.client):
            checksum = hashlib.sha256(token.encode('utf-8')).hexdigest()
            RefreshToken = get_refresh_token_model()
            families = set(RefreshToken.objects.filter(
                application=request.client, token_checksum=checksum,
            ).values_list('token_family', flat=True))
            families.update(RefreshToken.objects.filter(
                application=request.client, access_token__token_checksum=checksum,
            ).values_list('token_family', flat=True))
            for session in ClientLoginSession.objects.filter(application=request.client, token_family__in=families):
                revoke_session(session, 'logout')
        return super().revoke_token(token, token_type_hint, request, *args, **kwargs)

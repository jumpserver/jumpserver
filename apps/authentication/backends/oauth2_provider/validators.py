from datetime import timedelta
import math

from django.utils import timezone
from oauth2_provider.models import get_access_token_model, get_grant_model, get_refresh_token_model
from oauth2_provider.oauth2_validators import OAuth2Validator
from oauthlib.common import generate_token
from oauthlib.oauth2 import InvalidGrantError, InvalidRequestError

from authentication.services.client_login_session import (
    client_login_policy, client_policy_transaction, client_session_data,
    client_refresh_is_valid, is_client_application, validate_client_access_token,
)


class ClientOAuth2Validator(OAuth2Validator):
    def rotate_refresh_token(self, request):
        # Reuse the client token rows; save_bearer_token still rotates both values.
        if is_client_application(request.client):
            return False
        return super().rotate_refresh_token(request)

    def validate_bearer_token(self, token, scopes, request):
        if not super().validate_bearer_token(token, scopes, request):
            return False
        validate_client_access_token(request.access_token)
        return True

    def validate_refresh_token(self, refresh_token, client, request, *args, **kwargs):
        if not super().validate_refresh_token(refresh_token, client, request, *args, **kwargs):
            return False
        if not is_client_application(client):
            return True
        refresh = request.refresh_token_instance
        return client_refresh_is_valid(refresh, client_login_policy())

    def save_bearer_token(self, token, request, *args, **kwargs):
        if not is_client_application(request.client):
            return super().save_bearer_token(token, request, *args, **kwargs)
        with client_policy_transaction():
            policy = client_login_policy()
            if any(policy.values()) and dict(request.decoded_body or []).get('client_login_policy_version') != '1':
                raise InvalidRequestError(description='Please upgrade the JumpServer client to use the configured login policy.')
            refresh = getattr(request, 'refresh_token_instance', None)
            now = timezone.now()
            if refresh is not None:
                refresh = get_refresh_token_model().objects.select_for_update().select_related('user').filter(
                    pk=refresh.pk, application=request.client,
                ).first()
                # Recheck after the lock: a concurrent refresh, logout or policy
                # update may have invalidated the credentials since validation.
                if (not refresh or refresh.token != request.refresh_token
                        or not client_refresh_is_valid(refresh, policy)):
                    raise InvalidGrantError(description='Client login session expired.')
                request.refresh_token_instance = refresh
            elif request.grant_type != 'authorization_code':
                raise InvalidGrantError(description='Client authorization is required.')
            elif not get_grant_model().objects.filter(
                application=request.client, code=request.code, expires__gt=now,
            ).exists():
                raise InvalidGrantError(description='Client authorization has been revoked.')

            authenticated_at = refresh.created if refresh else now
            lifetime = policy['max_session_time']
            remaining = ((authenticated_at + timedelta(minutes=lifetime)) - now).total_seconds() if lifetime else None
            if remaining is not None:
                if remaining <= 0:
                    raise InvalidGrantError(description='Client login session expired.')
                token['expires_in'] = min(token['expires_in'], math.ceil(remaining))
            result = super().save_bearer_token(token, request, *args, **kwargs)
            if refresh:
                # ponytail: DOT 2.4's reuse path saves only the access-token row.
                # Keep RefreshToken.created as login time and its id for tickets;
                # on a DOT upgrade, verify this hook before upgrading.
                token['refresh_token'] = generate_token()
                get_refresh_token_model().objects.filter(pk=refresh.pk).update(token=token['refresh_token'])
                refresh.token = token['refresh_token']
            else:
                refresh = get_refresh_token_model().objects.get(token=token['refresh_token'], revoked__isnull=True)
            if lifetime:
                deadline = refresh.created + timedelta(minutes=lifetime)
                access = get_access_token_model().objects.get(pk=refresh.access_token_id)
                if timezone.now() >= deadline:
                    raise InvalidGrantError(description='Client login session expired.')
                if access.expires > deadline:
                    access.expires = deadline
                    access.save(update_fields=('expires',))
                token['expires_in'] = max(0, math.ceil((access.expires - timezone.now()).total_seconds()))
            token.update(client_session_data(refresh, policy))
            return result

    def revoke_token(self, token, token_type_hint, request, *args, **kwargs):
        if not is_client_application(request.client):
            return super().revoke_token(token, token_type_hint, request, *args, **kwargs)
        with client_policy_transaction():
            RefreshToken = get_refresh_token_model()
            refresh = RefreshToken.objects.filter(application=request.client, token=token, revoked__isnull=True).first()
            if refresh is None:
                refresh = RefreshToken.objects.filter(application=request.client, access_token__token=token).first()
            if refresh:
                refresh.revoke()

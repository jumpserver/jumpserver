import json
from urllib.parse import urlparse

import fido2.features
from django.conf import settings
from django.utils import timezone
from fido2.server import Fido2Server
from fido2.utils import websafe_decode, websafe_encode
from fido2.webauthn import PublicKeyCredentialRpEntity, AttestedCredentialData, PublicKeyCredentialUserEntity
from rest_framework.serializers import ValidationError
from user_agents.parsers import parse as ua_parse

from .models import UserPasskey

try:
    fido2.features.webauthn_json_mapping.enabled = True
except:
    pass


def get_current_platform(request):
    ua = ua_parse(request.META["HTTP_USER_AGENT"])
    if 'Safari' in ua.browser.family:
        return "Apple"
    elif 'Chrome' in ua.browser.family and ua.os.family == "Mac OS X":
        return "Chrome on Apple"
    elif 'Android' in ua.os.family:
        return "Google"
    elif "Windows" in ua.os.family:
        return "Microsoft"
    else:
        return "Key"


def get_server(request=None):
    """Get Server Info from settings and returns a Fido2Server"""
    if callable(settings.FIDO_SERVER_ID):
        fido_server_id = settings.FIDO_SERVER_ID(request)
    else:
        fido_server_id = settings.FIDO_SERVER_ID

    if callable(settings.FIDO_SERVER_NAME):
        fido_server_name = settings.FIDO_SERVER_NAME(request)
    else:
        fido_server_name = settings.FIDO_SERVER_NAME

    rp = PublicKeyCredentialRpEntity(id=fido_server_id, name=fido_server_name)
    return Fido2Server(rp)


def get_user_credentials(user):
    user_passkeys = UserPasskey.objects.filter(user=user)
    return [AttestedCredentialData(websafe_decode(uk.token)) for uk in user_passkeys]


def register_begin(request):
    server = get_server(request)
    user = request.user
    user_credentials = get_user_credentials(user)

    try:
        site_url = urlparse(settings.SITE_URL)
        prefix = site_url.netloc.split('.')[0]
    except:
        prefix = 'JumpServer'

    prefix = '(' + prefix + ')'
    user_entity = PublicKeyCredentialUserEntity(
        id=str(user.id).encode('utf8'),
        name=user.username + prefix,
        display_name=user.name,
    )
    auth_attachment = getattr(settings, 'KEY_ATTACHMENT', None)
    data, state = server.register_begin(
        user_entity, user_credentials,
        authenticator_attachment=auth_attachment,
        resident_key_requirement=fido2.webauthn.ResidentKeyRequirement.PREFERRED
    )
    request.session['fido2_state'] = state
    data = dict(data)
    return data, state


def register_complete(request):
    if not request.session.get("fido2_state"):
        raise ValidationError("No state found")
    data = request.data
    server = get_server(request)
    state = request.session.pop("fido2_state")
    auth_data = server.register_complete(state, response=data)
    encoded = websafe_encode(auth_data.credential_data)
    platform = get_current_platform(request)
    name = data.pop("key_name", '') or platform
    passkey = UserPasskey.objects.create(
        user=request.user,
        token=encoded,
        name=name,
        platform=platform,
        credential_id=data.get('id')
    )
    return passkey


def auth_begin(request):
    server = get_server(request)
    credentials = []
    username = None
    if "base_username" in request.session:
        username = request.session["base_username"]
    if request.user.is_authenticated:
        username = request.user.username
    if username:
        credentials = get_user_credentials(username)
    auth_data, state = server.authenticate_begin(credentials)
    request.session['fido2_state'] = state
    return auth_data


def auth_complete(request):
    server = get_server(request)
    data = request.data.get("passkeys")
    data = json.loads(data)
    credential_id = data['id']

    keys = UserPasskey.objects.filter(credential_id=credential_id, enabled=1)
    if not keys.exists():
        raise ValidationError("No key found")

    key = keys[0]
    credentials = [AttestedCredentialData(websafe_decode(key.token))]

    server.authenticate_complete(
        request.session.pop('fido2_state'),
        credentials=credentials,
        response=data
    )

    key.last_used = timezone.now()
    cross_platform = get_current_platform(request) != key.platform
    request.session["passkey"] = {
        'passkey': True,
        'name': key.name,
        'id': key.id,
        'platform': key.platform,
        'cross_platform': cross_platform
    }
    key.save()
    return key.user

# -*- coding: utf-8 -*-
# @Time    : 2019/11/22 1:49 下午
# @Author  : Alex
# @Email   : 1374462869@qq.com
# @Project : jumpserver
# @File    : backends.py
from django.contrib.auth.backends import ModelBackend
from django.conf import settings
import requests
from django.utils.http import urlencode
from .models import OIDCUser
from django.utils.encoding import force_bytes, smart_text
from common.utils import get_logger
from django.contrib.auth import get_user_model
from django.db import transaction
from .signals import post_create_openid_user
logger = get_logger(__file__)

class OIDCAuthBackend(ModelBackend):
    def authenticate(self, request, nonce=None, **kwargs):
        logger.info('Authentication OpenID password backend')
        redirect_uri = settings.BASE_SITE_URL + str(settings.LOGIN_COMPLETE_URL)
        if request is None:
            return
        code = request.GET.get('code')
        token_payload = {
            'client_id': settings.AUTH_OPENID_CLIENT_ID,
            'client_secret': settings.AUTH_OPENID_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
        }
        token_response = requests.post(settings.AUTH_OPENID_TOKEN_ENDPOINT, data=token_payload)
        token_response.raise_for_status()
        token_response_data = token_response.json()
        access_token = token_response_data.get('access_token')
        request.session['oidc_auth_access_token'] = access_token
        request_params = request.GET.dict()
        request_params.update({
            "access_token": access_token,
        })
        query = urlencode(request_params)
        userinfo_response = requests.get(
            '{url}?{query}'.format(url=settings.AUTH_OPENID_USERINFO_ENDPOINT, query=query))
        userinfo_response.raise_for_status()
        userinfo_data = userinfo_response.json()
        try:
            oidc_user = OIDCUser.objects.select_related('user').get(username=userinfo_data.get('username'))
        except OIDCUser.DoesNotExist:
            oidc_user, user = create_oidc_user_from_claims(userinfo_data)
            post_create_openid_user.send(sender=user.__class__, user=user)
            # oidc_user_created.send(sender=self.__class__, request=request, oidc_user=oidc_user)
        else:
            update_oidc_user_from_claims(oidc_user, userinfo_data)

        return oidc_user.user

def get_or_create_user(username, email):
    username = smart_text(username)

    try:
        user = get_user_model().objects.get(username=username, email=email)
    except get_user_model().DoesNotExist:
        user = get_user_model().objects.create_user(name=username, username=username, email=email)

    return user

@transaction.atomic
def create_oidc_user_from_claims(userinfo_data):
    """ Creates an ``OIDCUser`` instance using the claims extracted from an id_token. """
    username = userinfo_data['username']
    # email = userinfo_data.get('email')
    # u = base64.urlsafe_b64encode(hashlib.sha1(force_bytes(username)).digest()).rstrip(b'=')
    # user = get_or_create_user(u, email)
    user, _ = get_user_model().objects.update_or_create(
        username=username,
        defaults={
            'name': userinfo_data.get('displayName', ''),
            'email': userinfo_data.get('email', ''),
            'first_name': userinfo_data.get('given_name', ''),
            'last_name': userinfo_data.get('family_name', '')
        }
    )
    oidc_user = OIDCUser.objects.create(user=user, username=username, userinfo=userinfo_data)

    return oidc_user, user


@transaction.atomic
def update_oidc_user_from_claims(oidc_user, claims):
    """ Updates an ``OIDCUser`` instance using the claims extracted from an id_token. """
    oidc_user.userinfo = claims
    oidc_user.save()
    oidc_user.user.email = claims.get('email')
    oidc_user.user.save()
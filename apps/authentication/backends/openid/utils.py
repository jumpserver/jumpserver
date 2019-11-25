# -*- coding: utf-8 -*-
#

from django.conf import settings
from .models import Client

__all__ = ['new_client']


def new_client():
    """
    :return: authentication.models.Client
    """
    return Client(
        server_url=settings.AUTH_OPENID_SERVER_URL,
        realm_name=settings.AUTH_OPENID_REALM_NAME,
        client_id=settings.AUTH_OPENID_CLIENT_ID,
        client_secret=settings.AUTH_OPENID_CLIENT_SECRET
    )

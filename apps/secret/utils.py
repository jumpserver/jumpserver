# -*- coding: utf-8 -*-
#
from django.conf import settings

from common.utils import get_logger
from assets.const import StorageType
from .backends import Secret

logger = get_logger(__name__)


def get_secret_data(instance, name=None):
    if not instance:
        return
    fields = instance.SECRET_FIELD
    backend = settings.SECRET_STORAGE_BACKEND
    if backend != StorageType.db:
        client = Secret(instance, backend)
        secret_data = client.get_secret()
        if name:
            return secret_data.get(name, '')
        else:
            return {i: secret_data.get(i, '') for i in fields}
    else:
        if name:
            return getattr(instance, name)
        else:
            return {i: getattr(instance, i) for i in fields}


def replace_secret(instance, name=None):
    secret_data = get_secret_data(instance)
    if not secret_data:
        return
    if not name:
        for k, v in secret_data.items():
            setattr(instance, k, v)
    else:
        setattr(instance, name, secret_data)

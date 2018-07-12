# -*- coding: utf-8 -*-
#
import re
from django.apps import apps

from .models import Organization

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()


def get_org_from_request(request):
    oid = request.session.get("oid")
    org = Organization.get_instance(oid)
    return org


def get_current_request():
    return getattr(_thread_locals, 'request', None)


def get_current_org():
    return getattr(_thread_locals, 'current_org', None)


def get_current_user():
    return getattr(_thread_locals, 'user', None)


def set_current_org(org):
    setattr(_thread_locals, 'current_org', org)


def get_model_by_db_table(db_table):
    for model in apps.get_models():
        if model._meta.db_table == db_table:
            return model
    else:
        # here you can do fallback logic if no model with db_table found
        raise ValueError('No model found with db_table {}!'.format(db_table))

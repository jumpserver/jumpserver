# -*- coding: utf-8 -*-
#
from functools import partial
from werkzeug.local import Local

from common.utils import LocalProxy
from .models import Organization


_thread_locals = Local()


def get_org_from_request(request):
    oid = request.session.get("oid")
    if not oid:
        oid = request.META.get("HTTP_X_JMS_ORG")
    org = Organization.get_instance(oid)
    return org


def set_current_org(org):
    setattr(_thread_locals, 'current_org', org)


def set_to_default_org():
    set_current_org(Organization.default())


def set_to_root_org():
    set_current_org(Organization.root())


def _find(attr):
    return getattr(_thread_locals, attr, None)


def get_current_org():
    return _find('current_org')


def get_current_org_id():
    org = get_current_org()
    org_id = str(org.id) if org.is_real() else ''
    return org_id


current_org = LocalProxy(partial(_find, 'current_org'))

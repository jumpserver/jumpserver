# -*- coding: utf-8 -*-
#
from werkzeug.local import LocalProxy

from common.local import thread_local
from .models import Organization


def get_org_from_request(request):
    oid = request.session.get("oid")
    if not oid:
        oid = request.META.get("HTTP_X_JMS_ORG")
    if not oid:
        oid = Organization.DEFAULT_ID
    org = Organization.get_instance(oid)
    return org


def set_current_org(org):
    setattr(thread_local, 'current_org_id', org.id)


def set_to_default_org():
    set_current_org(Organization.default())


def set_to_root_org():
    set_current_org(Organization.root())


def _find(attr):
    return getattr(thread_local, attr, None)


def get_current_org():
    org_id = get_current_org_id()
    if org_id is None:
        return None
    org = Organization.get_instance(org_id)
    return org


def get_current_org_id():
    org_id = _find('current_org_id')
    return org_id


def get_current_org_id_for_serializer():
    org_id = get_current_org_id()
    if org_id == Organization.DEFAULT_ID:
        org_id = ''
    return org_id


current_org = LocalProxy(get_current_org)

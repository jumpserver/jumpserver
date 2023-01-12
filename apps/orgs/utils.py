# -*- coding: utf-8 -*-
#
import uuid
from inspect import signature
from functools import wraps
from werkzeug.local import LocalProxy
from contextlib import contextmanager

from common.local import thread_local
from .models import Organization


def get_org_from_request(request):
    # query中优先级最高
    oid = request.GET.get("oid")

    # 其次header
    if not oid:
        oid = request.META.get("HTTP_X_JMS_ORG")
    # 其次cookie
    if not oid:
        oid = request.COOKIES.get('X-JMS-ORG')
    # 其次session
    if not oid:
        oid = request.session.get("oid")

    if not oid:
        oid = Organization.DEFAULT_ID
    if oid.lower() == "default":
        oid = Organization.DEFAULT_ID
    elif oid.lower() == "root":
        oid = Organization.ROOT_ID
    org = Organization.get_instance(oid, default=Organization.default())
    return org


def set_current_org(org):
    if isinstance(org, (str, uuid.UUID)):
        org = Organization.get_instance(org)
    setattr(thread_local, 'current_org_id', org.id)


def set_to_default_org():
    set_current_org(Organization.default())


def set_to_root_org():
    set_current_org(Organization.root())


def set_to_system_org():
    set_current_org(Organization.system())


def _find(attr):
    return getattr(thread_local, attr, None)


def get_current_org():
    org_id = get_current_org_id()
    if not org_id or org_id == Organization.ROOT_ID:
        return Organization.root()
    org = Organization.get_instance(org_id, default=Organization.root())
    return org


def get_current_org_id():
    org_id = _find('current_org_id')
    return org_id


def get_current_org_id_for_serializer():
    org_id = get_current_org_id()
    return org_id


@contextmanager
def tmp_to_root_org():
    ori_org = get_current_org()
    set_to_root_org()
    yield
    if ori_org is not None:
        set_current_org(ori_org)


@contextmanager
def tmp_to_org(org):
    ori_org = get_current_org()
    set_current_org(org)
    yield
    if ori_org is not None:
        set_current_org(ori_org)


@contextmanager
def tmp_to_builtin_org(system=0, default=0):
    if system:
        org_id = Organization.SYSTEM_ID
    elif default:
        org_id = Organization.DEFAULT_ID
    else:
        raise ValueError("Must set system or default")
    ori_org = get_current_org()
    set_current_org(org_id)
    yield
    if ori_org is not None:
        set_current_org(ori_org)


def filter_org_queryset(queryset):
    locking_org = getattr(queryset.model, 'LOCKING_ORG', None)
    org = get_current_org()

    if locking_org:
        kwargs = {'org_id': locking_org}
    elif org is None or org.is_root():
        kwargs = {}
    else:
        kwargs = {'org_id': org.id}

    # import traceback
    # lines = traceback.format_stack()
    # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    # for line in lines[-10:-1]:
    #     print(line)
    # print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    queryset = queryset.filter(**kwargs)
    return queryset


def org_aware_func(org_arg_name):
    """
    :param org_arg_name: 函数中包含org_id的对象是哪个参数
    :return:
    """
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            sig = signature(func)
            values = sig.bind(*args, **kwargs)
            org_aware_resource = values.arguments.get(org_arg_name)
            if not org_aware_resource:
                return func(*args, **kwargs)
            if hasattr(org_aware_resource, '__getitem__'):
                org_aware_resource = org_aware_resource[0]
            if not hasattr(org_aware_resource, "org_id"):
                print("Error: {} not has org_id attr".format(org_aware_resource))
                return func(*args, **kwargs)
            with tmp_to_org(org_aware_resource.org_id):
                # print("Current org id: {}".format(org_aware_resource.org_id))
                return func(*args, **kwargs)
        return wrapper
    return decorate


current_org = LocalProxy(get_current_org)


def ensure_in_real_or_default_org(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_org or current_org.is_root():
            raise ValueError('You must in a real or default org!')
        return func(*args, **kwargs)
    return wrapper

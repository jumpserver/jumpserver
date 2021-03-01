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
    org = Organization.get_instance(oid, True)
    return org


def set_current_org(org):
    if isinstance(org, (str, uuid.UUID)):
        org = Organization.get_instance(org)
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
        return Organization.root()
    org = Organization.get_instance(org_id)
    return org


def get_current_org_id():
    org_id = _find('current_org_id')
    return org_id


def construct_org_mapper():
    orgs = Organization.objects.all()
    org_mapper = {str(org.id): org for org in orgs}
    default_org = Organization.default()
    org_mapper.update({
        '': default_org,
        Organization.DEFAULT_ID: default_org,
        Organization.ROOT_ID: Organization.root(),
        Organization.SYSTEM_ID: Organization.system()
    })
    return org_mapper


def set_org_mapper(org_mapper):
    setattr(thread_local, 'org_mapper', org_mapper)


def get_org_mapper():
    org_mapper = _find('org_mapper')
    if org_mapper is None:
        org_mapper = construct_org_mapper()
        set_org_mapper(org_mapper)
    return org_mapper


def get_org_by_id(org_id):
    org_id = str(org_id)
    org_mapper = get_org_mapper()
    org = org_mapper.get(org_id)
    return org


def get_org_name_by_id(org_id):
    org = get_org_by_id(org_id)
    if org:
        org_name = org.name
    else:
        org_name = 'Not Found'
    return org_name


def get_current_org_id_for_serializer():
    org_id = get_current_org_id()
    if org_id == Organization.DEFAULT_ID:
        org_id = ''
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


def get_org_filters():
    kwargs = {}

    _current_org = get_current_org()
    if _current_org is None:
        return kwargs

    if _current_org.is_real():
        kwargs['org_id'] = _current_org.id
    elif _current_org.is_default():
        kwargs["org_id"] = ''
    return kwargs


def filter_org_queryset(queryset):
    kwargs = get_org_filters()

    #
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

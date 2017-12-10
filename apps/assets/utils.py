# ~*~ coding: utf-8 ~*~
#
from common.utils import get_object_or_none
from .models import Asset, SystemUser


def get_assets_by_id_list(id_list):
    return Asset.objects.filter(id__in=id_list)


def get_assets_by_hostname_list(hostname_list):
    return Asset.objects.filter(hostname__in=hostname_list)


def get_system_user_by_name(name):
    system_user = get_object_or_none(SystemUser, name=name)
    return system_user

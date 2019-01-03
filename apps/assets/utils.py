# ~*~ coding: utf-8 ~*~
#
import os
import paramiko
from paramiko.ssh_exception import SSHException

from common.utils import get_object_or_none
from .models import Asset, SystemUser, Label


def get_assets_by_id_list(id_list):
    return Asset.objects.filter(id__in=id_list).filter(is_active=True)


def get_system_users_by_id_list(id_list):
    return SystemUser.objects.filter(id__in=id_list)


def get_assets_by_fullname_list(hostname_list):
    return Asset.get_queryset_by_fullname_list(hostname_list)


def get_system_user_by_name(name):
    system_user = get_object_or_none(SystemUser, name=name)
    return system_user


def get_system_user_by_id(id):
    system_user = get_object_or_none(SystemUser, id=id)
    return system_user


class LabelFilter:
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        query_keys = self.request.query_params.keys()
        all_label_keys = Label.objects.values_list('name', flat=True)
        valid_keys = set(all_label_keys) & set(query_keys)
        labels_query = {}
        for key in valid_keys:
            labels_query[key] = self.request.query_params.get(key)

        conditions = []
        for k, v in labels_query.items():
            query = {'labels__name': k, 'labels__value': v}
            conditions.append(query)

        if conditions:
            for kwargs in conditions:
                queryset = queryset.filter(**kwargs)
        return queryset

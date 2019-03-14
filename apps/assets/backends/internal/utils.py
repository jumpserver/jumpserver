# -*- coding: utf-8 -*-
#

from assets.models import AuthBook


def construct_authbook_object(asset_user, asset):
    """
    作用: 将<AssetUser>对象构造成为<AuthBook>对象并返回

    :param asset_user: <AdminUser>或<SystemUser>对象
    :param asset: <Asset>对象
    :return: <AuthBook>对象
    """
    fields = [
        'id', 'name', 'username', 'comment', 'org_id',
        '_password', '_private_key', '_public_key',
        'date_created', 'date_updated', 'created_by'
    ]

    obj = AuthBook(asset=asset, version=0, is_latest=True)
    for field in fields:
        value = getattr(asset_user, field)
        setattr(obj, field, value)
    return obj


# -*- coding: utf-8 -*-
#
from django.db import models

from common.mixins.models import CommonModelMixin


__all__ = ['FavoriteAsset']


class FavoriteAsset(CommonModelMixin):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'asset')

    @classmethod
    def get_user_favorite_assets_id(cls, user):
        return cls.objects.filter(user=user).values_list('asset', flat=True)

    @classmethod
    def get_user_favorite_assets(cls, user):
        from assets.models import Asset
        query_name = cls.asset.field.related_query_name()
        return Asset.objects.filter(**{f'{query_name}__user_id': user.id}).distinct()

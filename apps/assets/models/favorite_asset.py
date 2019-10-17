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

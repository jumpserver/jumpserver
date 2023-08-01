# -*- coding: utf-8 -*-
#
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel

__all__ = ['FavoriteAsset']


class FavoriteAsset(JMSBaseModel):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'asset')
        verbose_name = _("Favorite asset")

    @classmethod
    def get_user_favorite_asset_ids(cls, user):
        return cls.objects.filter(user=user).values_list('asset', flat=True)

    def __str__(self):
        return '%s' % self.asset

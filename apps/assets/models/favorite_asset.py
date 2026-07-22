# -*- coding: utf-8 -*-
#
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel

__all__ = ['FavoriteAsset', 'FavoriteFolder']


class FavoriteFolder(JMSBaseModel):
    """User custom favorite folder, owned by a user, visible across orgs, supports nesting"""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True, related_name='children'
    )

    class Meta:
        unique_together = ('user', 'name', 'parent')
        verbose_name = _("Favorite folder")

    def __str__(self):
        return self.name


class FavoriteAsset(JMSBaseModel):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE)
    folder = models.ForeignKey(
        'assets.FavoriteFolder', on_delete=models.CASCADE,
        null=True, blank=True, related_name='assets'
    )

    class Meta:
        unique_together = ('user', 'asset')
        verbose_name = _("Favorite asset")

    @classmethod
    def get_user_favorite_asset_ids(cls, user):
        return cls.objects.filter(user=user).values_list('asset', flat=True)

    def __str__(self):
        return '%s' % self.asset

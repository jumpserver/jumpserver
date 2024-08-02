from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel

__all__ = ['MyAsset']


class MyAsset(JMSBaseModel):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, related_name='my_assets')
    name = models.CharField(verbose_name=_("Custom Name"), max_length=128, default='')
    comment = models.CharField(verbose_name=_("Custom Comment"), max_length=512, default='')
    custom_fields = ['name', 'comment']

    class Meta:
        unique_together = ('user', 'asset')
        verbose_name = _("My asset")

    def custom_to_dict(self):
        data = {}
        for field in self.custom_fields:
            value = getattr(self, field)
            if value == "":
                continue
            data.update({field: value})
        return data

    @staticmethod
    def set_asset_custom_value(assets, user):
        my_assets = MyAsset.objects.filter(asset__in=assets, user=user).all()
        customs = {my_asset.asset.id: my_asset.custom_to_dict() for my_asset in my_assets}
        for asset in assets:
            custom = customs.get(asset.id)
            if not custom:
                continue
            for field, value in custom.items():
                if not hasattr(asset, field):
                    continue
                setattr(asset, field, value)

    def __str__(self):
        return f'{self.user}-{self.asset}'

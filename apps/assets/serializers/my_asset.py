# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from ..models import MyAsset

__all__ = ['MyAssetSerializer']


class MyAssetSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    name = serializers.CharField(label=_("Custom Name"), max_length=128, allow_blank=True, required=False)
    comment = serializers.CharField(label=_("Custom Comment"), max_length=512, allow_blank=True, required=False)

    class Meta:
        model = MyAsset
        fields = ['user', 'asset', 'name', 'comment']
        validators = []

    def create(self, data):
        custom_fields = MyAsset.custom_fields
        asset = data['asset']
        user = self.context['request'].user
        defaults = {field: data.get(field, '') for field in custom_fields}
        obj, created = MyAsset.objects.get_or_create(defaults=defaults, user=user, asset=asset)
        if created:
            return obj
        for field in custom_fields:
            value = data.get(field)
            if value is None:
                continue
            setattr(obj, field, value)
        obj.save()
        return obj

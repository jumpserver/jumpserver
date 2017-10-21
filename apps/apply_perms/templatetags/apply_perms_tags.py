# ~*~ coding: utf-8 ~*~

from django import template
from django.utils import timezone
from django.conf import settings
import json

register = template.Library()

@register.filter
def id_to_name(instance, member):
    attr = getattr(instance, member)
    result=""
    if member == 'user_groups':
        from users.models import UserGroup
        for user_group in UserGroup.objects.filter(id__in=json.loads(attr)):
            result += user_group.name + ','

    if member == 'assets':
        from assets.models import Asset
        for asset in Asset.objects.filter(id__in=json.loads(attr)):
            result += asset.hostname + ","

    if member == 'asset_groups':
        from assets.models import AssetGroup
        for asset_group in AssetGroup.objects.filter(id__in=json.loads(attr)):
            result += asset_group.name + ","

    if member == 'system_users':
        from assets.models import SystemUser
        for system_user in SystemUser.objects.filter(id__in=json.loads(attr)):
            result += system_user.username + ","

    return result.rstrip(',')

# ~*~ coding: utf-8 ~*~

import os
import urllib
import hashlib

from django import template
from django.utils import timezone
from django.conf import settings


register = template.Library()


@register.filter
def join_queryset_attr(queryset, attr, delimiter=', '):
    return delimiter.join([getattr(obj, attr, '') for obj in queryset])


@register.filter
def is_expired(datetime):
    if datetime > timezone.now():
        return False
    else:
        return True


@register.filter
def user_avatar_url(user):
    if user.avatar:
        return user.avatar.url
    else:
        default_dir = os.path.join(settings.MEDIA_ROOT, 'avatar', 'default')
        if os.path.isdir(default_dir):
            default_avatar_list = os.listdir(default_dir)
            default_avatar = default_avatar_list[len(user.username) % len(default_avatar_list)]
            return os.path.join(settings.MEDIA_URL, 'avatar', 'default',  default_avatar)
    return 'https://www.gravatar.com/avatar/c6812ab450230979465d7bf288eadce2a?s=120&d=identicon'

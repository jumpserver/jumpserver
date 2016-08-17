# ~*~ coding: utf-8 ~*~

import urllib
import hashlib

from django import template
from django.utils import timezone
from django.conf import settings
from django.conf.urls.static import static


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
def user_avatar_url(user, size=64):
    if user.avatar:
        return user.avatar.url
    gravatar_url = "https://www.gravatar.com/avatar/" \
                   + hashlib.md5(user.email.lower()).hexdigest() + "?"
    gravatar_url += urllib.urlencode({'d': 'identicon', 's': str(size)})
    return gravatar_url




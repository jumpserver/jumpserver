# ~*~ coding: utf-8 ~*~

from django import template
from django.utils import timezone


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

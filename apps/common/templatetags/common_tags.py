# ~*~ coding: utf-8 ~*~

from django import template
from django.utils import timezone
from django.conf import settings


register = template.Library()


@register.filter
def join_queryset_attr(queryset, attr, delimiter=', '):
    return delimiter.join([getattr(obj, attr, '') for obj in queryset])


@register.filter
def pagination_range(total_page, current_num=1, display=5):
    """Return Page range

    :param total_page: Total numbers of paginator
    :param current_num: current display page num
    :param display: Display as many as [:display:] page

    In order to display many page num on web like:
    < 1 2 3 4 5 >
    """
    try:
        current_num = int(current_num)
    except ValueError:
        current_num = 1

    start = current_num - display/2 if current_num > display/2 else 1
    end = start + display if start + display <= total_page else total_page + 1

    return range(start, end)
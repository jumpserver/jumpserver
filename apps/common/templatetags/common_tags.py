# ~*~ coding: utf-8 ~*~

from django import template
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.html import escape
from django import forms

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

    half_display = int(display/2)
    start = current_num - half_display if current_num > half_display else 1
    if start + display <= total_page:
        end = start + display
    else:
        end = total_page + 1
        start = end - display if end > display else 1

    return range(start, end)


@register.filter
def join_attr(seq, attr=None, sep=None):
    if sep is None:
        sep = ', '
    if attr is not None:
        seq = [getattr(obj, attr) for obj in seq]
    return sep.join(seq)


@register.filter
def int_to_str(value):
    return str(value)


@register.filter
def ts_to_date(ts):
    try:
        ts = float(ts)
    except (TypeError, ValueError):
        ts = 0
    dt = timezone.datetime.fromtimestamp(ts).\
        replace(tzinfo=timezone.get_current_timezone())
    return dt.strftime('%Y-%m-%d %H:%M:%S')


@register.filter
def to_html(s):
    return escape(s).replace('\n', '<br />')


@register.filter
def time_util_with_seconds(date_from, date_to):
    if not date_from:
        return ''
    if not date_to:
        return ''
        date_to = timezone.now()

    delta = date_to - date_from
    seconds = delta.seconds
    if seconds < 60:
        return '{} s'.format(seconds)
    elif seconds < 60*60:
        return '{} m'.format(seconds//60)
    else:
        return '{} h'.format(seconds//3600)


@register.filter
def is_bool_field(field):
    if isinstance(field, forms.BooleanField):
        return True
    else:
        return False


@register.filter
def is_image_field(field):
    if isinstance(field, forms.ImageField):
        return True
    else:
        return False


@register.filter
def to_dict(data):
    return dict(data)


@register.filter
def sort(data):
    return sorted(data)


@register.filter
def subtract(value, arg):
    return value - arg


@register.filter
def state_show(state):
    success = '<i class ="fa fa-check text-navy"> </i>'
    failed = '<i class ="fa fa-times text-danger"> </i>'
    if state:
        return success
    else:
        return failed

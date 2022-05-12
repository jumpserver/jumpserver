import datetime

import pytz
from django.utils import timezone as dj_timezone
from rest_framework.fields import DateTimeField

max = datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)


def astimezone(dt: datetime.datetime, tzinfo: pytz.tzinfo.DstTzInfo):
    assert dj_timezone.is_aware(dt)
    return tzinfo.normalize(dt.astimezone(tzinfo))


def as_china_cst(dt: datetime.datetime):
    return astimezone(dt, pytz.timezone('Asia/Shanghai'))


def as_current_tz(dt: datetime.datetime):
    return astimezone(dt, dj_timezone.get_current_timezone())


def utc_now():
    return dj_timezone.now()


def local_now():
    return dj_timezone.localtime(dj_timezone.now())


def local_now_display(fmt='%Y-%m-%d %H:%M:%S'):
    return local_now().strftime(fmt)


def local_now_date_display(fmt='%Y-%m-%d'):
    return local_now().strftime(fmt)


_rest_dt_field = DateTimeField()
dt_parser = _rest_dt_field.to_internal_value
dt_formatter = _rest_dt_field.to_representation

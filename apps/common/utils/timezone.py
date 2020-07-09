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


def utcnow():
    return dj_timezone.now()


def now():
    return as_current_tz(utcnow())


_rest_dt_field = DateTimeField()
dt_parser = _rest_dt_field.to_internal_value
dt_formater = _rest_dt_field.to_representation

from datetime import datetime, timedelta

from django.utils import timezone as dj_timezone
from rest_framework.fields import DateTimeField


def as_current_tz(dt: datetime):
    return dt.astimezone(dj_timezone.get_current_timezone())


def utc_now():
    return dj_timezone.now()


def local_now():
    return dj_timezone.localtime(dj_timezone.now())


def local_now_display(fmt='%Y-%m-%d %H:%M:%S'):
    return local_now().strftime(fmt)


def local_now_filename():
    return local_now().strftime('%Y%m%d-%H%M%S')


def local_now_date_display(fmt='%Y-%m-%d'):
    return local_now().strftime(fmt)


def local_zero_hour(fmt='%Y-%m-%d'):
    return datetime.strptime(local_now().strftime(fmt), fmt)


def local_monday():
    zero_hour_time = local_zero_hour()
    return zero_hour_time - timedelta(zero_hour_time.weekday())


_rest_dt_field = DateTimeField()
dt_parser = _rest_dt_field.to_internal_value
dt_formatter = _rest_dt_field.to_representation

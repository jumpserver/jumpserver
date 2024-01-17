import copy
from datetime import datetime
from itertools import chain

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.db import models
from django.db.models import F, Value, CharField
from django.db.models.functions import Concat

from common.db.fields import RelatedManager
from common.utils import validate_ip, get_ip_city, get_logger
from common.utils.timezone import as_current_tz
from .const import DEFAULT_CITY

logger = get_logger(__name__)


def write_login_log(*args, **kwargs):
    from audits.models import UserLoginLog

    ip = kwargs.get('ip') or ''
    if not (ip and validate_ip(ip)):
        ip = ip[:15]
        city = DEFAULT_CITY
    else:
        city = get_ip_city(ip) or DEFAULT_CITY
    kwargs.update({'ip': ip, 'city': city})
    return UserLoginLog.objects.create(**kwargs)


def _get_instance_field_value(
        instance, include_model_fields,
        model_need_continue_fields, exclude_fields=None
):
    data = {}
    opts = getattr(instance, '_meta', None)
    if opts is not None:
        for f in chain(opts.concrete_fields, opts.private_fields):
            if not include_model_fields and not getattr(f, 'primary_key', False):
                continue

            if isinstance(f, GenericForeignKey):
                continue

            if isinstance(f, (models.FileField, models.ImageField)):
                continue

            if getattr(f, 'attname', None) in model_need_continue_fields:
                continue

            value = getattr(instance, f.name, None) or getattr(instance, f.attname, None)
            if not isinstance(value, bool) and not value:
                continue

            if getattr(f, 'primary_key', False):
                f.verbose_name = 'id'
            elif isinstance(value, list):
                value = copy.deepcopy(value)
            elif isinstance(value, dict):
                value = dict(copy.deepcopy(value))
            elif isinstance(value, datetime):
                value = as_current_tz(value).strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, RelatedManager):
                value = value.value
            elif isinstance(f, models.OneToOneField) and isinstance(value, models.Model):
                nested_data = _get_instance_field_value(
                    value, include_model_fields, model_need_continue_fields, ('id',)
                )
                for k, v in nested_data.items():
                    if exclude_fields and k in exclude_fields:
                        continue
                    data.setdefault(k, v)
                continue
            elif isinstance(f, GenericRelation):
                value = [str(v) for v in value.all()]
            elif isinstance(f, GenericForeignKey):
                continue
            try:
                data.setdefault(str(f.verbose_name), value)
            except Exception as e:
                print(f.__dict__)
                raise e
    return data


def model_to_dict_for_operate_log(
        instance, include_model_fields=True, include_related_fields=None
):
    def get_related_values(f):
        value = []
        if instance.pk is not None:
            related_name = getattr(f, 'attname', '') or getattr(f, 'related_name', '')
            if not related_name or related_name in ['history_passwords']:
                return
            try:
                value = [str(i) for i in getattr(instance, related_name).all()]
            except:
                pass
        if not value:
            return
        try:
            field_key = getattr(f, 'verbose_name', None) or f.related_model._meta.verbose_name
            data.setdefault(str(field_key), value)
        except:
            pass

    data = _get_instance_field_value(
        instance, include_model_fields, ['date_updated']
    )

    if include_related_fields:
        opts = instance._meta
        for f in chain(opts.many_to_many, opts.related_objects):
            related_model = getattr(f, 'related_model', None)
            if related_model not in include_related_fields:
                continue
            get_related_values(f)

    return data


def construct_userlogin_usernames(user_queryset):
    usernames_original = user_queryset.values_list('username', flat=True)
    usernames_combined = user_queryset.annotate(
        usernames_combined_field=Concat(F('name'), Value('('), F('username'), Value(')'), output_field=CharField())
    ).values_list("usernames_combined_field", flat=True)
    usernames = list(chain(usernames_original, usernames_combined))
    return usernames

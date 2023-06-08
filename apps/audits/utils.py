import codecs
import copy
from itertools import chain
from datetime import datetime

from django.db import models
from django.http import HttpResponse

from common.utils.timezone import as_current_tz
from common.utils import validate_ip, get_ip_city, get_logger
from .const import DEFAULT_CITY

logger = get_logger(__name__)


def get_excel_response(filename):
    excel_response = HttpResponse(content_type='text/csv')
    excel_response[
        'Content-Disposition'] = 'attachment; filename="%s"' % filename
    excel_response.write(codecs.BOM_UTF8)
    return excel_response


def write_content_to_excel(response, header=None, login_logs=None, fields=None):
    writer = csv.writer(response, dialect='excel', quoting=csv.QUOTE_MINIMAL)
    if header:
        writer.writerow(header)
    if login_logs:
        for log in login_logs:
            data = [getattr(log, field.name) for field in fields]
            writer.writerow(data)
    return response


def write_login_log(*args, **kwargs):
    from audits.models import UserLoginLog

    ip = kwargs.get('ip') or ''
    if not (ip and validate_ip(ip)):
        ip = ip[:15]
        city = DEFAULT_CITY
    else:
        city = get_ip_city(ip) or DEFAULT_CITY
    kwargs.update({'ip': ip, 'city': city})
    UserLoginLog.objects.create(**kwargs)


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

            if isinstance(f, (models.FileField, models.ImageField)):
                continue

            if getattr(f, 'attname', None) in model_need_continue_fields:
                continue

            value = getattr(instance, f.name) or getattr(instance, f.attname)
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
            elif isinstance(f, models.OneToOneField) and isinstance(value, models.Model):
                nested_data = _get_instance_field_value(
                    value, include_model_fields, model_need_continue_fields, ('id',)
                )
                for k, v in nested_data.items():
                    if exclude_fields and k in exclude_fields:
                        continue
                    data.setdefault(k, v)
                continue
            data.setdefault(str(f.verbose_name), value)
    return data


def model_to_dict_for_operate_log(
        instance, include_model_fields=True, include_related_fields=False
):
    model_need_continue_fields = ['date_updated']
    m2m_need_continue_fields = ['history_passwords']

    data = _get_instance_field_value(
        instance, include_model_fields, model_need_continue_fields
    )

    if include_related_fields:
        opts = instance._meta
        for f in opts.many_to_many:
            value = []
            if instance.pk is not None:
                related_name = getattr(f, 'attname', '') or getattr(f, 'related_name', '')
                if not related_name or related_name in m2m_need_continue_fields:
                    continue
                try:
                    value = [str(i) for i in getattr(instance, related_name).all()]
                except:
                    pass
            if not value:
                continue
            try:
                field_key = getattr(f, 'verbose_name', None) or f.related_model._meta.verbose_name
                data.setdefault(str(field_key), value)
            except:
                pass
    return data

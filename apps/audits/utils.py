import csv
import codecs

from itertools import chain

from django.http import HttpResponse
from django.db import models

from settings.serializers import SettingsSerializer
from common.utils import validate_ip, get_ip_city, get_logger
from common.db import fields
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


def get_resource_display(resource):
    resource_display = str(resource)
    setting_serializer = SettingsSerializer()
    label = setting_serializer.get_field_label(resource_display)
    if label is not None:
        resource_display = label
    return resource_display


def model_to_dict_for_operate_log(
        instance, include_model_fields=True, include_related_fields=True
):
    need_continue_fields = ['date_updated']
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields):
        if isinstance(f, (models.FileField, models.ImageField)):
            continue

        if getattr(f, 'attname', None) in need_continue_fields:
            continue

        value = getattr(instance, f.name) or getattr(instance, f.attname)
        if not isinstance(value, bool) and not value:
            continue

        if getattr(f, 'primary_key', False):
            f.verbose_name = 'id'
        elif isinstance(f, (
            fields.EncryptCharField, fields.EncryptTextField,
            fields.EncryptJsonDictCharField, fields.EncryptJsonDictTextField
        )) or getattr(f, 'attname', '') == 'password':
            value = 'encrypt|%s' % value
        elif isinstance(value, list):
            value = [str(v) for v in value]

        if include_model_fields or getattr(f, 'primary_key', False):
            data[str(f.verbose_name)] = value

    if include_related_fields:
        for f in chain(opts.many_to_many, opts.related_objects):
            value = []
            if instance.pk is not None:
                related_name = getattr(f, 'attname', '') or getattr(f, 'related_name', '')
                if related_name:
                    try:
                        value = [str(i) for i in getattr(instance, related_name).all()]
                    except:
                        pass
            if not value:
                continue
            try:
                field_key = getattr(f, 'verbose_name', None) or f.related_model._meta.verbose_name
                data[str(field_key)] = value
            except:
                pass
    return data

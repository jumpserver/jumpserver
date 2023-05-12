import codecs
import copy
import csv
import os

import jms_storage

from itertools import chain
from datetime import datetime

from django.conf import settings
from django.db import models
from django.http import HttpResponse

from common.utils.timezone import as_current_tz
from common.utils import validate_ip, get_ip_city, get_logger
from terminal.models import default_storage, ReplayStorage
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
            elif isinstance(value, (list, dict)):
                value = copy.deepcopy(value)
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


def find_ftp_log_file_local(ftp_log):
    local_path = ftp_log.get_file_local_path()

    # 去default storage中查找
    if default_storage.exists(local_path):
        url = default_storage.url(local_path)
        return local_path, url
    return None, None


def download_file(remote_path, local_path):
    replay_storages = ReplayStorage.objects.all()
    configs = {
        storage.name: storage.config
        for storage in replay_storages
        if not storage.type_null_or_server
    }
    if settings.SERVER_REPLAY_STORAGE:
        storages = ReplayStorage.objects.filter(id=settings.SERVER_REPLAY_STORAGE)
        if len(storages) == 0:
            logger.warn('Cannot find replayStorage: ' + settings.SERVER_REPLAY_STORAGE)
        else:
            storage = storages[0].meta
            storage['TYPE'] = storages[0].type
            configs['SERVER_REPLAY_STORAGE'] = storage
    if not configs:
        msg = "Not found FTP file, and not remote storage set"
        return None, msg

    # 保存到storage的路径
    target_path = os.path.join(default_storage.base_location, local_path)
    target_dir = os.path.dirname(target_path)
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    storage = jms_storage.get_multi_object_storage(configs)
    ok, err = storage.download(remote_path, target_path)
    if not ok:
        msg = "Failed download file from {} to {}: {}".format(remote_path, target_path, err)
        logger.error(msg)
        return None, "Failed download file: {}".format(err)
    url = default_storage.url(local_path)
    return local_path, url


def download_ftp_log_file(ftp_log):
    remote_path = ftp_log.get_file_remote_path()
    local_path = ftp_log.get_file_local_path()
    return download_file(remote_path, local_path)


def get_ftp_log_file_url(ftp_log):
    local_path, url = find_ftp_log_file_local(ftp_log)
    if local_path is None:
        local_path, url = download_ftp_log_file(ftp_log)
    return local_path, url

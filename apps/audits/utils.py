import csv
import codecs

from django.http import HttpResponse
from django.db import transaction
from django.utils import translation

from audits.models import OperateLog
from common.utils import validate_ip, get_ip_city, get_request_ip, get_logger
from jumpserver.utils import current_request
from .const import DEFAULT_CITY, MODELS_NEED_RECORD


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


def create_operate_log(action, sender, resource):
    user = current_request.user if current_request else None
    if not user or not user.is_authenticated:
        return
    model_name = sender._meta.object_name
    if model_name not in MODELS_NEED_RECORD:
        return
    with translation.override('en'):
        resource_type = sender._meta.verbose_name
    remote_addr = get_request_ip(current_request)

    data = {
        "user": str(user), 'action': action, 'resource_type': resource_type,
        'resource': str(resource), 'remote_addr': remote_addr,
    }
    with transaction.atomic():
        try:
            OperateLog.objects.create(**data)
        except Exception as e:
            logger.error("Create operate log error: {}".format(e))

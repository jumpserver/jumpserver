import csv
import codecs

from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.utils.translation import ugettext as _

from common.utils import validate_ip, get_ip_city, get_logger

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
    default_city = _("Unknown")
    ip = kwargs.get('ip') or ''
    if not (ip and validate_ip(ip)):
        ip = ip[:15]
        city = default_city
    else:
        city = get_ip_city(ip) or default_city
    kwargs.update({'ip': ip, 'city': city})
    UserLoginLog.objects.create(**kwargs)


def download_ftplog_file(ftp_log, md5_file_name):
    remote_path = ftp_log.get_file_remote_path(md5_file_name)  # 存在外部存储上的路径
    local_path = ftp_log.get_file_local_path(md5_file_name)
    from terminal.utils import download_file
    return download_file(remote_path, local_path)


def get_ftplog_file_url(ftp_log, md5_file_name):
    local_path, url = find_ftplog_file_local(ftp_log, md5_file_name)
    if local_path is None:
        local_path, url = download_ftplog_file(ftp_log, md5_file_name)
    return local_path, url


def find_ftplog_file_local(ftp_log, file_name):
    local_path = ftp_log.get_file_local_path(file_name)

    # 去default storage中查找
    if default_storage.exists(local_path):
        url = default_storage.url(local_path)
        return local_path, url
    return None, None

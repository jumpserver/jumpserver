# -*- coding: utf-8 -*-
#
from django.dispatch import receiver
from django.db import transaction

from audits.models import (
    PasswordChangeLog, UserLoginLog, FTPLog, OperateLog
)
from audits.serializers import (
    UserLoginLogSerializer, FTPLogSerializer, OperateLogSerializer,
    PasswordChangeLogSerializer
)
from common.utils import get_request_ip, get_syslogger
from common.utils.encode import data_to_json
from jumpserver.utils import current_request
from users.models import User
from users.signals import post_user_change_password
from terminal.models import Session, Command
from terminal.serializers import SessionSerializer, SessionCommandSerializer


sys_logger = get_syslogger(__name__)


@receiver(post_user_change_password, sender=User)
def on_user_change_password(sender, user=None, **kwargs):
    if not current_request:
        remote_addr = '127.0.0.1'
        change_by = 'System'
    else:
        remote_addr = get_request_ip(current_request)
        if not current_request.user.is_authenticated:
            change_by = str(user)
        else:
            change_by = str(current_request.user)
    with transaction.atomic():
        PasswordChangeLog.objects.create(
            user=str(user), change_by=change_by,
            remote_addr=remote_addr,
        )


def on_audits_log_create(sender, instance=None, **kwargs):
    if sender == UserLoginLog:
        category = "login_log"
        serializer_cls = UserLoginLogSerializer
    elif sender == FTPLog:
        category = "ftp_log"
        serializer_cls = FTPLogSerializer
    elif sender == OperateLog:
        category = "operation_log"
        serializer_cls = OperateLogSerializer
    elif sender == PasswordChangeLog:
        category = "password_change_log"
        serializer_cls = PasswordChangeLogSerializer
    elif sender == Session:
        category = "host_session_log"
        serializer_cls = SessionSerializer
    elif sender == Command:
        category = "session_command_log"
        serializer_cls = SessionCommandSerializer
    else:
        return

    serializer = serializer_cls(instance)
    data = data_to_json(serializer.data, indent=None)
    msg = "{} - {}".format(category, data)
    sys_logger.info(msg)

# -*- coding: utf-8 -*-
#
import uuid

from django.db.models.signals import (
    post_save, m2m_changed, pre_delete, pre_save
)
from django.dispatch import receiver
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.functional import LazyObject
from django.contrib.auth import BACKEND_SESSION_KEY
from django.utils.translation import ugettext_lazy as _
from django.utils import translation
from rest_framework.renderers import JSONRenderer
from rest_framework.request import Request

from users.models import User
from assets.models import Asset, SystemUser, CommandFilter
from terminal.models import Session, Command
from perms.models import AssetPermission, ApplicationPermission
from rbac.models import Role

from audits.utils import model_to_dict_for_operate_log as model_to_dict
from audits.handler import (
    get_instance_current_with_cache_diff, cache_instance_before_data,
    create_or_update_operate_log, get_instance_dict_from_cache
)
from authentication.signals import post_auth_failed, post_auth_success
from authentication.utils import check_different_city_login_if_need
from jumpserver.utils import current_request
from users.signals import post_user_change_password
from .utils import write_login_log
from . import models, serializers
from .models import OperateLog
from .const import MODELS_NEED_RECORD
from terminal.backends.command.serializers import SessionCommandSerializer
from terminal.serializers import SessionSerializer
from common.const.signals import POST_ADD, POST_REMOVE, POST_CLEAR, SKIP_SIGNAL
from common.utils import get_request_ip_or_data, get_logger, get_syslogger
from common.utils.encode import data_to_json

logger = get_logger(__name__)
sys_logger = get_syslogger(__name__)
json_render = JSONRenderer()


class AuthBackendLabelMapping(LazyObject):
    @staticmethod
    def get_login_backends():
        backend_label_mapping = {}
        for source, backends in User.SOURCE_BACKEND_MAPPING.items():
            for backend in backends:
                backend_label_mapping[backend] = source.label
        backend_label_mapping[settings.AUTH_BACKEND_PUBKEY] = _('SSH Key')
        backend_label_mapping[settings.AUTH_BACKEND_MODEL] = _('Password')
        backend_label_mapping[settings.AUTH_BACKEND_SSO] = _('SSO')
        backend_label_mapping[settings.AUTH_BACKEND_AUTH_TOKEN] = _('Auth Token')
        backend_label_mapping[settings.AUTH_BACKEND_WECOM] = _('WeCom')
        backend_label_mapping[settings.AUTH_BACKEND_FEISHU] = _('FeiShu')
        backend_label_mapping[settings.AUTH_BACKEND_DINGTALK] = _('DingTalk')
        backend_label_mapping[settings.AUTH_BACKEND_TEMP_TOKEN] = _('Temporary token')
        return backend_label_mapping

    def _setup(self):
        self._wrapped = self.get_login_backends()


AUTH_BACKEND_LABEL_MAPPING = AuthBackendLabelMapping()

M2M_ACTION = {
    POST_ADD: OperateLog.ACTION_CREATE,
    POST_REMOVE: OperateLog.ACTION_DELETE,
    POST_CLEAR: OperateLog.ACTION_DELETE,
}


@receiver(m2m_changed)
def on_m2m_changed(sender, action, instance, reverse, model, pk_set, **kwargs):
    if action not in M2M_ACTION:
        return
    if not instance:
        return

    resource_type = instance._meta.verbose_name
    current_instance = model_to_dict(instance, include_model_fields=False)

    instance_id = current_instance.get('id')
    log_id, before_instance = get_instance_dict_from_cache(instance_id)

    field_name = str(model._meta.verbose_name)
    objs = model.objects.filter(pk__in=pk_set)
    objs_display = [str(o) for o in objs]
    action = M2M_ACTION[action]
    changed_field = current_instance.get(field_name, [])

    after, before, before_value = None, None, None
    if action == OperateLog.ACTION_CREATE:
        before_value = list(set(changed_field) - set(objs_display))
    elif action == OperateLog.ACTION_DELETE:
        before_value = list(
            set(changed_field).symmetric_difference(set(objs_display))
        )

    if changed_field:
        after = {field_name: changed_field}
    if before_value:
        before = {field_name: before_value}

    if sorted(str(before)) == sorted(str(after)):
        return

    create_or_update_operate_log(
        OperateLog.ACTION_UPDATE, resource_type,
        resource=instance, log_id=log_id, before=before, after=after
    )


def signal_of_operate_log_whether_continue(sender, instance, created, update_fields=None):
    condition = True
    if not instance:
        condition = False
    if instance and getattr(instance, SKIP_SIGNAL, False):
        condition = False
    # 终端模型的 create 事件由系统产生，不记录
    if instance._meta.object_name == 'Terminal' and created:
        condition = False
    # last_login 改变是最后登录日期, 每次登录都会改变
    if instance._meta.object_name == 'User' and \
            update_fields and 'last_login' in update_fields:
        condition = False
    # 不在记录白名单中，跳过
    if sender._meta.object_name not in MODELS_NEED_RECORD:
        condition = False
    return condition


@receiver(pre_save)
def on_object_pre_create_or_update(sender, instance=None, raw=False, using=None, update_fields=None, **kwargs):
    ok = signal_of_operate_log_whether_continue(
        sender, instance, False, update_fields
    )
    if not ok:
        return
    instance_before_data = {'id': instance.id}
    raw_instance = type(instance).objects.filter(pk=instance.id).first()
    if raw_instance:
        instance_before_data = model_to_dict(raw_instance)
    operate_log_id = str(uuid.uuid4())
    instance_before_data['operate_log_id'] = operate_log_id
    setattr(instance, 'operate_log_id', operate_log_id)
    cache_instance_before_data(instance_before_data)


@receiver(post_save)
def on_object_created_or_update(sender, instance=None, created=False, update_fields=None, **kwargs):
    ok = signal_of_operate_log_whether_continue(
        sender, instance, created, update_fields
    )
    if not ok:
        return

    log_id, before, after = None, None, None
    if created:
        action = models.OperateLog.ACTION_CREATE
        after = model_to_dict(instance)
        log_id = getattr(instance, 'operate_log_id', None)
    else:
        action = models.OperateLog.ACTION_UPDATE
        current_instance = model_to_dict(instance)
        log_id, before, after = get_instance_current_with_cache_diff(current_instance)

    resource_type = sender._meta.verbose_name
    create_or_update_operate_log(
        action, resource_type, resource=instance,
        log_id=log_id, before=before, after=after
    )


@receiver(pre_delete)
def on_object_delete(sender, instance=None, **kwargs):
    ok = signal_of_operate_log_whether_continue(sender, instance, False)
    if not ok:
        return

    resource_type = sender._meta.verbose_name
    create_or_update_operate_log(
        models.OperateLog.ACTION_DELETE, resource_type,
        resource=instance, before=model_to_dict(instance)
    )


@receiver(post_user_change_password, sender=User)
def on_user_change_password(sender, user=None, **kwargs):
    if not current_request:
        remote_addr = '127.0.0.1'
        change_by = 'System'
    else:
        remote_addr = get_request_ip_or_data(current_request)
        if not current_request.user.is_authenticated:
            change_by = str(user)
        else:
            change_by = str(current_request.user)
    with transaction.atomic():
        models.PasswordChangeLog.objects.create(
            user=str(user), change_by=change_by,
            remote_addr=remote_addr,
        )


def on_audits_log_create(sender, instance=None, **kwargs):
    if sender == models.UserLoginLog:
        category = "login_log"
        serializer_cls = serializers.UserLoginLogSerializer
    elif sender == models.FTPLog:
        category = "ftp_log"
        serializer_cls = serializers.FTPLogSerializer
    elif sender == models.OperateLog:
        category = "operation_log"
        serializer_cls = serializers.OperateLogSerializer
    elif sender == models.PasswordChangeLog:
        category = "password_change_log"
        serializer_cls = serializers.PasswordChangeLogSerializer
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


def get_login_backend(request):
    backend = request.session.get('auth_backend', '') or \
              request.session.get(BACKEND_SESSION_KEY, '')

    backend_label = AUTH_BACKEND_LABEL_MAPPING.get(backend, None)
    if backend_label is None:
        backend_label = ''
    return backend_label


def generate_data(username, request, login_type=None):
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    login_ip = get_request_ip_or_data(request) or '0.0.0.0'

    if login_type is None and isinstance(request, Request):
        login_type = request.META.get('HTTP_X_JMS_LOGIN_TYPE', 'U')
    if login_type is None:
        login_type = 'W'

    with translation.override('en'):
        backend = str(get_login_backend(request))

    data = {
        'username': username,
        'ip': login_ip,
        'type': login_type,
        'user_agent': user_agent[0:254],
        'datetime': timezone.now(),
        'backend': backend,
    }
    return data


@receiver(post_auth_success)
def on_user_auth_success(sender, user, request, login_type=None, **kwargs):
    logger.debug('User login success: {}'.format(user.username))
    check_different_city_login_if_need(user, request)
    data = generate_data(user.username, request, login_type=login_type)
    request.session['login_time'] = data['datetime'].strftime("%Y-%m-%d %H:%M:%S")
    data.update({'mfa': int(user.mfa_enabled), 'status': True})
    write_login_log(**data)


@receiver(post_auth_failed)
def on_user_auth_failed(sender, username, request, reason='', **kwargs):
    logger.debug('User login failed: {}'.format(username))
    data = generate_data(username, request)
    data.update({'reason': reason[:128], 'status': False})
    write_login_log(**data)

# -*- coding: utf-8 -*-
#
import uuid

from django.apps import apps
from django.db.models.signals import post_save, pre_save, m2m_changed, pre_delete
from django.dispatch import receiver
from django.utils import translation

from audits.handler import (
    get_instance_current_with_cache_diff, cache_instance_before_data,
    create_or_update_operate_log, get_instance_dict_from_cache
)
from audits.utils import model_to_dict_for_operate_log as model_to_dict
from common.const.signals import POST_ADD, POST_REMOVE, POST_CLEAR, SKIP_SIGNAL
from common.signals import django_ready
from jumpserver.utils import current_request
from ..const import MODELS_NEED_RECORD, ActionChoices

M2M_ACTION = {
    POST_ADD: ActionChoices.create,
    POST_REMOVE: ActionChoices.delete,
    POST_CLEAR: ActionChoices.delete,
}


@receiver(m2m_changed)
def on_m2m_changed(sender, action, instance, reverse, model, pk_set, **kwargs):
    if action not in M2M_ACTION:
        return
    if not instance:
        return

    with translation.override('en'):
        resource_type = instance._meta.verbose_name
        current_instance = model_to_dict(
            instance, include_model_fields=False, include_related_fields=[model]
        )

        instance_id = current_instance.get('id')
        log_id, before_instance = get_instance_dict_from_cache(instance_id)

        field_name = str(model._meta.verbose_name)
        pk_set = pk_set or {}
        objs = model.objects.filter(pk__in=pk_set)
        objs_display = [str(o) for o in objs]
        action = M2M_ACTION[action]
        changed_field = current_instance.get(field_name, [])

        after, before, before_value = None, None, None
        if action == ActionChoices.create:
            before_value = list(set(changed_field) - set(objs_display))
        elif action == ActionChoices.delete:
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
            ActionChoices.update, resource_type,
            resource=instance, log_id=log_id, before=before, after=after
        )


def signal_of_operate_log_whether_continue(
        sender, instance, created, update_fields=None
):
    condition = True
    if not instance:
        condition = False
    if instance and getattr(instance, SKIP_SIGNAL, False):
        condition = False
    # 不记录组件的操作日志
    user = current_request.user if current_request else None
    if not user or getattr(user, 'is_service_account', False):
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
def on_object_pre_create_or_update(
        sender, instance=None, raw=False, using=None, update_fields=None, **kwargs
):
    ok = signal_of_operate_log_whether_continue(
        sender, instance, False, update_fields
    )
    if not ok:
        return
    with translation.override('en'):
        # users.PrivateToken Model 没有 id 有 pk字段
        instance_id = getattr(instance, 'id', getattr(instance, 'pk', None))
        instance_before_data = {'id': instance_id}
        raw_instance = type(instance).objects.filter(pk=instance_id).first()

        if raw_instance:
            instance_before_data = model_to_dict(raw_instance)
        operate_log_id = str(uuid.uuid4())
        instance_before_data['operate_log_id'] = operate_log_id
        setattr(instance, 'operate_log_id', operate_log_id)
        cache_instance_before_data(instance_before_data)


@receiver(post_save)
def on_object_created_or_update(
        sender, instance=None, created=False, update_fields=None, **kwargs
):
    ok = signal_of_operate_log_whether_continue(
        sender, instance, created, update_fields
    )
    if not ok:
        return
    with translation.override('en'):
        log_id, before, after = None, None, None
        if created:
            action = ActionChoices.create
            after = model_to_dict(instance)
            log_id = getattr(instance, 'operate_log_id', None)
        else:
            action = ActionChoices.update
            current_instance = model_to_dict(instance)
            log_id, before, after = get_instance_current_with_cache_diff(current_instance)

        resource_type = sender._meta.verbose_name
        object_name = sender._meta.object_name
        create_or_update_operate_log(
            action, resource_type, resource=instance, log_id=log_id,
            before=before, after=after, object_name=object_name
        )


@receiver(pre_delete)
def on_object_delete(sender, instance=None, **kwargs):
    ok = signal_of_operate_log_whether_continue(sender, instance, False)
    if not ok:
        return

    with translation.override('en'):
        resource_type = sender._meta.verbose_name
        create_or_update_operate_log(
            ActionChoices.delete, resource_type,
            resource=instance, before=model_to_dict(instance)
        )


@receiver(django_ready)
def on_django_start_set_operate_log_monitor_models(sender, **kwargs):
    exclude_apps = {
        'django_cas_ng', 'captcha', 'admin', 'jms_oidc_rp', 'audits',
        'django_celery_beat', 'contenttypes', 'sessions', 'auth',
    }
    exclude_models = {
        'UserPasswordHistory', 'ContentType',
        'MessageContent', 'SiteMessage',
        'PlatformAutomation', 'PlatformProtocol', 'Protocol',
        'HistoricalAccount', 'GatheredUser', 'ApprovalRule',
        'BaseAutomation', 'CeleryTask', 'Command', 'JobLog',
        'ConnectionToken', 'SessionJoinRecord',
        'HistoricalJob', 'Status', 'TicketStep', 'Ticket',
        'UserAssetGrantedTreeNodeRelation', 'TicketAssignee',
        'SuperTicket', 'SuperConnectionToken', 'PermNode',
        'PermedAsset', 'PermedAccount', 'MenuPermission',
        'Permission', 'TicketSession', 'ApplyLoginTicket',
        'ApplyCommandTicket', 'ApplyLoginAssetTicket',
        'FavoriteAsset', 'Asset'
    }
    for i, app in enumerate(apps.get_models(), 1):
        app_name = app._meta.app_label
        model_name = app._meta.object_name
        if app_name in exclude_apps or \
                model_name in exclude_models or \
                model_name.endswith('Execution'):
            continue
        MODELS_NEED_RECORD.add(model_name)

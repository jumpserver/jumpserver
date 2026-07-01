# -*- coding: utf-8 -*-
#
import uuid
from itertools import chain

from django.apps import apps
from django.db.models.signals import (
    pre_delete, pre_save, m2m_changed, post_delete, post_save
)
from django.dispatch import receiver
from django.utils import translation

from audits.handler import (
    get_instance_current_with_cache_diff, cache_instance_before_data,
    create_or_update_operate_log, get_instance_dict_from_cache
)
from audits.utils import model_to_dict_for_operate_log as model_to_dict
from common.const.signals import POST_ADD, POST_REMOVE, POST_CLEAR, OP_LOG_SKIP_SIGNAL
from common.signals import django_ready
from jumpserver.utils import current_request
from ..const import MODELS_NEED_RECORD, ActionChoices

M2M_ACTION = {
    POST_ADD: ActionChoices.create,
    POST_REMOVE: ActionChoices.delete,
    POST_CLEAR: ActionChoices.delete,
}


def _get_m2m_field_verbose_name(instance, model, sender):
    opts = instance._meta
    for f in chain(opts.many_to_many, opts.related_objects):
        related_model = getattr(f, 'related_model', None)
        if related_model != model:
            continue

        through = None
        remote_field = getattr(f, 'remote_field', None)
        if remote_field is not None:
            through = getattr(remote_field, 'through', None)
        if through is None:
            through = getattr(f, 'through', None)

        if through is not sender:
            continue

        verbose_name = getattr(f, 'verbose_name', None) or model._meta.verbose_name
        return str(verbose_name)
    return str(model._meta.verbose_name)


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

        instance_id_data = current_instance.get('id', {})
        if isinstance(instance_id_data, dict):
            instance_id = instance_id_data.get('value')
        else:
            instance_id = instance_id_data
        log_id, before_instance = get_instance_dict_from_cache(instance_id)

        field_name = _get_m2m_field_verbose_name(instance, model, sender)
        pk_set = pk_set or {}
        objs = model.objects.filter(pk__in=pk_set)
        objs_display = [str(o) for o in objs]
        action = M2M_ACTION[action]
        changed_field = current_instance.get(field_name, {})
        if not changed_field and field_name != str(model._meta.verbose_name):
            changed_field = current_instance.get(str(model._meta.verbose_name), {})
        changed_value = changed_field.get('value', [])

        after, before, before_value = None, None, None
        if action == ActionChoices.create:
            before_value = list(set(changed_value) - set(objs_display))
        elif action == ActionChoices.delete:
            before_value = list(set(changed_value).symmetric_difference(set(objs_display)))

        if changed_field:
            after = {field_name: changed_field}
        if before_value:
            before_change_field = changed_field.copy()
            before_change_field['value'] = before_value
            before = {field_name: before_change_field}

        if before == after:
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
    if instance and getattr(instance, OP_LOG_SKIP_SIGNAL, False):
        condition = False
    user = current_request.user if current_request else None
    if not user or getattr(user, 'is_service_account', False):
        condition = False
    if instance._meta.object_name == 'Terminal' and created:
        condition = False
    if instance._meta.object_name == 'User' and \
            update_fields and 'last_login' in update_fields:
        condition = False
    if sender._meta.object_name not in MODELS_NEED_RECORD:
        condition = False
    return condition


@receiver([pre_save, pre_delete])
def on_object_pre_create_or_update(
        sender, instance=None, raw=False, using=None, update_fields=None, **kwargs
):
    ok = signal_of_operate_log_whether_continue(
        sender, instance, False, update_fields
    )
    if not ok:
        return

    with translation.override('en'):
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


@receiver(post_delete)
def on_object_delete(sender, instance=None, **kwargs):
    ok = signal_of_operate_log_whether_continue(sender, instance, False)
    if not ok:
        return

    with translation.override('en'):
        resource_type = sender._meta.verbose_name
        action = getattr(sender, '_OPERATE_LOG_ACTION', {})
        action = action.get('delete', ActionChoices.delete)
        instance_id = getattr(instance, 'id', getattr(instance, 'pk', None))
        log_id, before = get_instance_dict_from_cache(instance_id)
        if not log_id:
            log_id, before = None, model_to_dict(instance)
        create_or_update_operate_log(
            action, resource_type, log_id=log_id,
            resource=instance, before=before,
        )


@receiver(django_ready)
def on_django_start_set_operate_log_monitor_models(sender, **kwargs):
    exclude_apps = {
        'django_cas_ng', 'captcha', 'admin', 'jms_oidc_rp', 'audits',
        'django_celery_beat', 'contenttypes', 'sessions', 'auth',
    }
    exclude_models = {
        'UserPasswordHistory', 'ContentType', 'Asset',
        'MessageContent', 'SiteMessage',
        'PlatformAutomation', 'PlatformProtocol', 'Protocol',
        'HistoricalAccount', 'GatheredUser', 'ApprovalRule',
        'BaseAutomation', 'CeleryTask', 'Command', 'JobLog',
        'ConnectionToken', 'SessionJoinRecord', 'SessionSharing',
        'HistoricalJob', 'Status', 'TicketStep', 'Ticket',
        'UserAssetGrantedTreeNodeRelation', 'TicketAssignee',
        'SuperTicket', 'SuperConnectionToken', 'AdminConnectionToken', 'PermNode',
        'PermedAsset', 'PermedAccount', 'MenuPermission',
        'Permission', 'TicketSession', 'ApplyLoginTicket',
        'ApplyCommandTicket', 'ApplyLoginAssetTicket',
        'FavoriteAsset', 'FavoriteFolder', 'ChangeSecretRecord', 'AppProvider', 'Variable', 'LeakPasswords'
    }
    include_models = {'UserSession'}
    for i, app in enumerate(apps.get_models(), 1):
        app_name = app._meta.app_label
        model_name = app._meta.object_name
        if app_name in exclude_apps or \
                model_name in exclude_models or \
                model_name.endswith('Execution'):
            if model_name not in include_models:
                continue
        MODELS_NEED_RECORD.add(model_name)

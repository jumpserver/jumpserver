# -*- coding: utf-8 -*-
#
from celery import signals
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _, gettext_noop

from accounts.const import AutomationTypes
from accounts.models import AccountBackupAutomation
from assets.models import Asset, Node
from audits.models import ActivityLog
from common.utils import get_object_or_none, i18n_fmt, get_logger
from jumpserver.utils import current_request
from ops.celery import app
from orgs.models import Organization
from orgs.utils import tmp_to_root_org, current_org
from terminal.models import Session
from users.models import User
from ..const import ActivityChoices
from ..models import UserLoginLog

logger = get_logger(__name__)


class TaskActivityHandler(object):

    @staticmethod
    def _func_accounts_execute_automation(*args, **kwargs):
        asset_ids = []
        pid, tp = kwargs.get('pid'), kwargs.get('tp')
        model = AutomationTypes.get_type_model(tp)
        task_type_label = tp.label
        with tmp_to_root_org():
            instance = get_object_or_none(model, pk=pid)
        if instance is not None:
            asset_ids = instance.get_all_assets().values_list('id', flat=True)
        return task_type_label, asset_ids

    @staticmethod
    def _func_accounts_push_accounts_to_assets(*args, **kwargs):
        return '', args[0][1]

    @staticmethod
    def _func_accounts_execute_account_backup_plan(*args, **kwargs):
        asset_ids, pid = [], kwargs.get('pid')
        with tmp_to_root_org():
            instance = get_object_or_none(AccountBackupAutomation, pk=pid)
        if instance is not None:
            asset_ids = Asset.objects.filter(
                platform__type__in=instance.types
            ).values_list('id', flat=True)
        return '', asset_ids

    @staticmethod
    def _func_assets_verify_accounts_connectivity(*args, **kwargs):
        return '', args[0][1]

    @staticmethod
    def _func_accounts_verify_accounts_connectivity(*args, **kwargs):
        return '', args[0][1]

    @staticmethod
    def _func_assets_test_assets_connectivity_manual(*args, **kwargs):
        return '', args[0][0]

    @staticmethod
    def _func_assets_test_node_assets_connectivity_manual(*args, **kwargs):
        asset_ids = []
        node = get_object_or_none(Node, pk=args[0][0])
        if node is not None:
            asset_ids = node.get_all_assets().values_list('id', flat=True)
        return '', asset_ids

    @staticmethod
    def _func_assets_update_assets_hardware_info_manual(*args, **kwargs):
        return '', args[0][0]

    @staticmethod
    def _func_assets_update_node_assets_hardware_info_manual(*args, **kwargs):
        asset_ids = []
        node = get_object_or_none(Node, pk=args[0][0])
        if node is not None:
            asset_ids = node.get_all_assets().values_list('id', flat=True)
        return '', asset_ids

    @staticmethod
    def get_task_display(task_name, **kwargs):
        task = app.tasks.get(task_name)
        return getattr(task, 'verbose_name', _('Unknown'))

    def get_info_by_task_name(self, task_name, *args, **kwargs):
        resource_ids = []
        task_name_list = str(task_name).split('.')
        if len(task_name_list) < 2:
            return '', resource_ids

        task_display = self.get_task_display(task_name)
        model, name = task_name_list[0], task_name_list[-1]
        func_name = '_func_%s_%s' % (model, name)
        handle_func = getattr(self, func_name, None)
        if handle_func is not None:
            task_type, resource_ids = handle_func(*args, **kwargs)
            if task_type:
                task_display = '%s-%s' % (task_display, task_type)
        return task_display, resource_ids


class ActivityLogHandler:
    @staticmethod
    def session_for_activity(obj):
        detail = i18n_fmt(
            gettext_noop('User %s use account %s login asset %s'),
            obj.user, obj.account, obj.asset
        )
        return [obj.asset_id, obj.user_id, obj.account_id], detail, ActivityChoices.session_log, obj.org_id

    @staticmethod
    def login_log_for_activity(obj):
        login_status = gettext_noop('Success') if obj.status else gettext_noop('Failed')
        detail = i18n_fmt(gettext_noop('User %s login system %s'), obj.username, login_status)

        username = obj.username
        user_id = User.objects.filter(username=username) \
            .values_list('id', flat=True).first()
        resource_list = []
        if user_id:
            resource_list = [user_id]
        return resource_list, detail, ActivityChoices.login_log, Organization.SYSTEM_ID

    @staticmethod
    def task_log_for_celery(headers, body):
        task_id, task_name = headers.get('id'), headers.get('task')
        task = app.tasks.get(task_name)
        if not task:
            raise ValueError('Task not found: {}'.format(task_name))
        activity_callback = getattr(task, 'activity_callback', None)
        if not callable(activity_callback):
            return [], '', ''
        args, kwargs = body[:2]
        data = activity_callback(*args, **kwargs)
        if data is None:
            return [], '', ''
        resource_ids, org_id, user = data + ('',) * (3 - len(data))
        if not user:
            user = str(current_request.user) if current_request else 'System'
        if org_id is None:
            org_id = current_org.org_id
        task_display = getattr(task, 'verbose_name', _('Unknown'))
        detail = i18n_fmt(
            gettext_noop('User %s perform a task for this resource: %s'),
            user, task_display
        )
        return resource_ids, detail, org_id


def create_activities(resource_ids, detail, detail_id, action, org_id):
    if not resource_ids:
        return
    activities = [
        ActivityLog(
            resource_id=getattr(resource_id, 'pk', resource_id),
            type=action, detail=detail, detail_id=detail_id, org_id=org_id
        )
        for resource_id in resource_ids
    ]
    ActivityLog.objects.bulk_create(activities)
    return activities


@signals.after_task_publish.connect
def after_task_publish_for_activity_log(headers=None, body=None, **kwargs):
    """ Tip: https://docs.celeryq.dev/en/stable/internals/protocol.html#message-protocol-task-v2 """
    try:
        task_id = headers.get('id')
        resource_ids, detail, org_id = ActivityLogHandler.task_log_for_celery(headers, body)
    except Exception as e:
        logger.error(f'Get celery task info error: {e}', exc_info=True)
    else:
        logger.debug(f'Create activity log for celery task: {task_id}')
        create_activities(resource_ids, detail, task_id, action=ActivityChoices.task, org_id=org_id)


model_activity_handler_map = {
    Session: ActivityLogHandler.session_for_activity,
    UserLoginLog: ActivityLogHandler.login_log_for_activity,
}


def on_session_or_login_log_created(sender, instance=None, created=False, **kwargs):
    if not created:
        return

    func = model_activity_handler_map.get(sender)
    if not func:
        logger.error('Activity log handler not found: {}'.format(sender))

    resource_ids, detail, act_type, org_id = func(instance)
    return create_activities(resource_ids, detail, instance.id, act_type, org_id)


for sd in [Session, UserLoginLog]:
    post_save.connect(on_session_or_login_log_created, sender=sd)

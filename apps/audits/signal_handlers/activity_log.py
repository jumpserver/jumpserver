# -*- coding: utf-8 -*-
#
from celery import signals
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _, gettext_noop

from accounts.const import AutomationTypes
from accounts.models import AccountBackupAutomation
from assets.models import Asset, Node
from audits.models import ActivityLog
from common.utils import get_object_or_none, i18n_fmt
from jumpserver.utils import current_request
from ops.celery import app
from orgs.utils import tmp_to_root_org
from orgs.models import Organization
from terminal.models import Session
from users.models import User
from ..const import ActivityChoices
from ..models import UserLoginLog


class ActivityLogHandler(object):

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

    def get_celery_task_info(self, task_name, *args, **kwargs):
        task_display, resource_ids = self.get_info_by_task_name(
            task_name, *args, **kwargs
        )
        return task_display, resource_ids

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
        user_id = User.objects.filter(username=obj.username).values('id').first()
        resource_list = []
        if user_id:
            resource_list = [user_id['id']]
        return resource_list, detail, ActivityChoices.login_log, Organization.SYSTEM_ID


activity_handler = ActivityLogHandler()


@signals.before_task_publish.connect
def before_task_publish_for_activity_log(headers=None, **kwargs):
    task_id, task_name = headers.get('id'), headers.get('task')
    args, kwargs = kwargs['body'][:2]
    task_display, resource_ids = activity_handler.get_celery_task_info(
        task_name, args, **kwargs
    )
    if not current_request:
        user = 'System'
    else:
        user = str(current_request.user)

    detail = i18n_fmt(
        gettext_noop('User %s perform a task (%s) for this resource'),
        user, task_display
    )
    activities = [
        ActivityLog(resource_id=resource_id, type=ActivityChoices.task, detail=detail)
        for resource_id in resource_ids
    ]
    ActivityLog.objects.bulk_create(activities)
    activity_info = {
        'activity_ids': [a.id for a in activities]
    }
    kwargs['activity_info'] = activity_info


@signals.task_prerun.connect
def on_celery_task_pre_run_for_activity_log(task_id='', **kwargs):
    activity_info = kwargs['kwargs'].pop('activity_info', None)
    if activity_info is None:
        return

    activities = []
    for activity_id in activity_info['activity_ids']:
        activities.append(
            ActivityLog(id=activity_id, detail_id=task_id)
        )
    ActivityLog.objects.bulk_update(activities, ('detail_id',))


def on_session_or_login_log_created(sender, instance=None, created=False, **kwargs):
    handler_mapping = {
        'Session': activity_handler.session_for_activity,
        'UserLoginLog': activity_handler.login_log_for_activity
    }
    model_name = sender._meta.object_name
    if not created or model_name not in handler_mapping:
        return

    resource_ids, detail, act_type, org_id = handler_mapping[model_name](instance)
    activities = [
        ActivityLog(
            resource_id=i, type=act_type, detail=detail,
            detail_id=instance.id, org_id=org_id
        )
        for i in resource_ids
    ]
    ActivityLog.objects.bulk_create(activities)


for sd in [Session, UserLoginLog]:
    post_save.connect(on_session_or_login_log_created, sender=sd)

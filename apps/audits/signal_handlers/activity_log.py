# -*- coding: utf-8 -*-
#

from celery import signals
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _, gettext_noop

from audits.models import ActivityLog
from common.utils import i18n_fmt, get_logger
from jumpserver.utils import current_request
from ops.celery import app
from orgs.models import Organization
from orgs.utils import current_org, tmp_to_org
from terminal.models import Session
from users.models import User
from ..const import ActivityChoices
from ..models import UserLoginLog

logger = get_logger(__name__)


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
        if not org_id:
            org_id = current_org.id
        task_display = getattr(task, 'verbose_name', _('Unknown'))
        detail = i18n_fmt(
            gettext_noop('User %s perform a task for this resource: %s'),
            user, task_display
        )
        return resource_ids, detail, org_id


def create_activities(resource_ids, detail, detail_id, action, org_id):
    if not resource_ids:
        return
    if not org_id:
        org_id = Organization.ROOT_ID
    activities = [
        ActivityLog(
            resource_id=getattr(resource_id, 'pk', resource_id),
            type=action, detail=detail, detail_id=detail_id, org_id=org_id
        )
        for resource_id in resource_ids
    ]
    with tmp_to_org(org_id):
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
        if not resource_ids:
            return
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
    if not resource_ids:
        return
    return create_activities(resource_ids, detail, instance.id, act_type, org_id)


for sd in [Session, UserLoginLog]:
    post_save.connect(on_session_or_login_log_created, sender=sd)

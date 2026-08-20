import asyncio
import os

import aiofiles
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from common.db.utils import close_old_connections
from common.utils import get_logger
from orgs.mixins.ws import OrgMixin
from orgs.utils import tmp_to_org
from rbac.builtin import BuiltinRole
from .ansible.utils import get_ansible_task_log_path
from .celery.utils import get_celery_task_log_path
from .const import CELERY_LOG_MAGIC_MARK
from .models import CeleryTaskExecution

logger = get_logger(__name__)


class TaskLogWebsocket(AsyncJsonWebsocketConsumer, OrgMixin):
    disconnected = False
    user_tasks = (
        'ops.tasks.run_ops_job',
        'ops.tasks.run_ops_job_execution',
    )

    log_types = {
        'celery': get_celery_task_log_path,
        'ansible': get_ansible_task_log_path
    }

    async def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            await self.accept()
            self.cookie = self.get_cookie()
            self.org = self.get_current_org()
        else:
            await self.close()

    def get_log_path(self, task_id, log_type):
        func = self.log_types.get(log_type)
        if func:
            return func(task_id)

    @sync_to_async
    def get_task(self, task_id):
        task = CeleryTaskExecution.objects.filter(id=task_id).first()
        # task.creator 是 foreign key, 会异步去查询的，在下面的 if task.creator 会报错, 所以这里先取出来
        if task and task.creator != ' ':
            return task
        else:
            return None

    @sync_to_async
    def get_current_user_role_ids(self, user):
        with tmp_to_org(self.org):
            org_roles = user.org_roles.all()
        system_roles = user.system_roles.all()
        roles = system_roles | org_roles
        user_role_ids = set(map(str, roles.values_list('id', flat=True)))
        return user_role_ids

    async def receive_json(self, content, **kwargs):
        task_id = content.get('task')
        task = await self.get_task(task_id)
        if not task:
            await self.send_json({'message': 'Task not found', 'task': task_id})
            return

        admin_auditor_role_ids = {
            BuiltinRole.system_admin.id,
            BuiltinRole.system_auditor.id,
            BuiltinRole.org_admin.id,
            BuiltinRole.org_auditor.id
        }
        user = self.scope['user']
        user_role_ids = await self.get_current_user_role_ids(user)
        has_admin_auditor_role = bool(admin_auditor_role_ids & user_role_ids)
        has_perms = await self.has_perms(user, ['audits.view_joblog'])
        user_can_view = task.creator == user or (task.name in self.user_tasks and has_perms)
        # (有管理员或审计员角色) 或者 (任务是用户自己创建的 或者 有查看任务日志权限), 其他情况没有权限
        if not (has_admin_auditor_role or user_can_view):
            await self.send_json({'message': 'No permission', 'task': task_id})
            return

        task_type = content.get('type', 'celery')
        log_path = self.get_log_path(task_id, task_type)
        await self.async_handle_task(task_id, log_path, task_type)

    async def async_handle_task(
            self, task_id, log_path, log_type='celery'
    ):
        logger.info("Task id: {}".format(task_id))
        status_check_interval = 10  # Check the task state every five seconds.
        status_check_countdown = 0
        last_task_state = None
        while not self.disconnected:
            if os.path.exists(log_path):
                await self.send_task_log(task_id, log_path)
                break

            if status_check_countdown <= 0:
                task = await self.get_task(task_id)
                if not task:
                    await self.send_json({
                        'event': 'unavailable', 'reason': 'task_not_found',
                        'message': '', 'task': task_id,
                    })
                    break

                if task.state != last_task_state:
                    await self.send_json({
                        'event': 'status', 'state': task.state,
                        'is_finished': task.is_finished,
                        'date_published': task.date_published.isoformat(),
                        'date_start': (
                            task.date_start.isoformat()
                            if task.date_start else None
                        ),
                        'date_finished': (
                            task.date_finished.isoformat()
                            if task.date_finished else None
                        ),
                        'task': task_id,
                    })
                    last_task_state = task.state

                if task.is_finished:
                    await self.send_json({
                        'event': 'unavailable', 'reason': 'finished_without_log',
                        'state': task.state, 'message': '', 'task': task_id,
                    })
                    break
                status_check_countdown = status_check_interval

            status_check_countdown -= 1
            await asyncio.sleep(0.5)

    async def send_task_log(self, task_id, log_path):
        await self.send_json({'message': '\r\n'})
        try:
            logger.debug('Task log path: {}'.format(log_path))
            async with aiofiles.open(log_path, 'rb') as task_log_f:
                while not self.disconnected:
                    data = await task_log_f.read(4096)
                    if data:
                        data = data.replace(b'\n', b'\r\n')
                        await self.send_json(
                            {'message': data.decode(errors='ignore'), 'task': task_id}
                        )
                        if data.find(CELERY_LOG_MAGIC_MARK) != -1:
                            await self.send_json(
                                {'event': 'end', 'task': task_id, 'message': ''}
                            )
                            logger.debug("Task log file magic mark found")
                            break
                    await asyncio.sleep(0.2)
        except OSError as e:
            logger.warning('Task log path open failed: {}'.format(e))

    async def disconnect(self, close_code):
        self.disconnected = True
        close_old_connections()

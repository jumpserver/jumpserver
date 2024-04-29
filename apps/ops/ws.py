import asyncio
import os

import aiofiles
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from common.db.utils import close_old_connections
from common.utils import get_logger
from .ansible.utils import get_ansible_task_log_path
from .celery.utils import get_celery_task_log_path
from .const import CELERY_LOG_MAGIC_MARK
from .models import CeleryTaskExecution

logger = get_logger(__name__)


class TaskLogWebsocket(AsyncJsonWebsocketConsumer):
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

    async def receive_json(self, content, **kwargs):
        task_id = content.get('task')
        task = await self.get_task(task_id)
        if not task:
            await self.send_json({'message': 'Task not found', 'task': task_id})
            return
        if task.name in self.user_tasks and task.creator != self.scope['user']:
            await self.send_json({'message': 'No permission', 'task': task_id})
            return

        task_type = content.get('type', 'celery')
        log_path = self.get_log_path(task_id, task_type)
        await self.async_handle_task(task_id, log_path)

    async def async_handle_task(self, task_id, log_path):
        logger.info("Task id: {}".format(task_id))
        timeout = 0
        while not self.disconnected:
            if timeout >= 60:
                await self.send_json({'message': '\r\n', 'task': task_id})
                await self.send_json({'message': 'Task log was not found, the directory may not be shared.',
                                      'task': task_id})
                break
            if not os.path.exists(log_path):
                await self.send_json({'message': '.', 'task': task_id})
                timeout += 0.5
                await asyncio.sleep(0.5)
            else:
                await self.send_task_log(task_id, log_path)
                break

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
            logger.warn('Task log path open failed: {}'.format(e))

    async def disconnect(self, close_code):
        self.disconnected = True
        close_old_connections()

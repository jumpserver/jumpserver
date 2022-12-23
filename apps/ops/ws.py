import asyncio
import os

import aiofiles
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from common.db.utils import close_old_connections
from common.utils import get_logger
from .ansible.utils import get_ansible_task_log_path
from .celery.utils import get_celery_task_log_path

logger = get_logger(__name__)


class TaskLogWebsocket(AsyncJsonWebsocketConsumer):
    disconnected = False

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

    async def receive_json(self, content, **kwargs):
        task_id = content.get('task')
        task_typ = content.get('type', 'celery')
        log_path = self.get_log_path(task_id, task_typ)
        await self.async_handle_task(task_id, log_path)

    async def async_handle_task(self, task_id, log_path):
        logger.info("Task id: {}".format(task_id))
        while not self.disconnected:
            if not os.path.exists(log_path):
                await self.send_json({'message': '.', 'task': task_id})
                await asyncio.sleep(0.5)
            else:
                await self.send_task_log(task_id, log_path)
                break

    async def send_task_log(self, task_id, log_path):
        await self.send_json({'message': '\r\n'})
        try:
            logger.debug('Task log path: {}'.format(log_path))
            task_end_mark = []
            async with aiofiles.open(log_path, 'rb') as task_log_f:
                while not self.disconnected:
                    data = await task_log_f.read(4096)
                    if data:
                        data = data.replace(b'\n', b'\r\n')
                        await self.send_json(
                            {'message': data.decode(errors='ignore'), 'task': task_id}
                        )
                        if data.find(b'succeeded in') != -1:
                            task_end_mark.append(1)
                        if data.find(bytes(task_id, 'utf8')) != -1:
                            task_end_mark.append(1)
                    elif len(task_end_mark) == 2:
                        logger.debug('Task log end: {}'.format(task_id))
                        await self.send_json({'event': 'end', 'task': task_id})
                        break
                    await asyncio.sleep(0.2)
        except OSError as e:
            logger.warn('Task log path open failed: {}'.format(e))
        # await self.close()

    async def disconnect(self, close_code):
        self.disconnected = True
        close_old_connections()

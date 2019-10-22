import time
import os
import threading
import json

from common.utils import get_logger

from .celery.utils import get_celery_task_log_path
from channels.generic.websocket import JsonWebsocketConsumer

logger = get_logger(__name__)


class CeleryLogWebsocket(JsonWebsocketConsumer):
    disconnected = False

    def connect(self):
        self.accept()

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = json.loads(text_data)
        task_id = data.get("task")
        if task_id:
            self.handle_task(task_id)

    def handle_task(self, task_id):
        logger.info("Task id: {}".format(task_id))
        log_path = get_celery_task_log_path(task_id)

        def func():
            task_log_f = None

            while not self.disconnected:
                if not os.path.exists(log_path):
                    self.send_json({'message': '.', 'task': task_id})
                    time.sleep(0.5)
                    continue
                self.send_json({'message': '\r\n'})
                try:
                    logger.debug('Task log path: {}'.format(log_path))
                    task_log_f = open(log_path, 'rb')
                    break
                except OSError:
                    return

            if not task_log_f:
                return

            task_end_mark = []

            while not self.disconnected:
                data = task_log_f.read(4096)

                if data:
                    data = data.replace(b'\n', b'\r\n')
                    self.send_json({'message': data.decode(errors='ignore'), 'task': task_id})
                    if data.find(b'succeeded in') != -1:
                        task_end_mark.append(1)
                    if data.find(bytes(task_id, 'utf8')) != -1:
                        task_end_mark.append(1)
                    if len(task_end_mark) == 2:
                        logger.debug('Task log end: {}'.format(task_id))
                        break
                time.sleep(0.1)
            task_log_f.close()
        thread = threading.Thread(target=func)
        thread.start()

    def disconnect(self, close_code):
        self.disconnected = True
        self.close()



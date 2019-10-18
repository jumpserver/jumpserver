import time
import os
import threading
import json

from celery.result import AsyncResult

from .celery.utils import get_celery_task_log_path
from channels.generic.websocket import JsonWebsocketConsumer


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
                    task_log_f = open(log_path)
                    break
                except OSError:
                    return

            while not self.disconnected:
                data = task_log_f.readline()
                if data:
                    data = data.replace('\n', '\r\n')
                    self.send_json({'message': data, 'task': task_id})
                    if data.startswith('Task') and data.find('succeeded'):
                        break
                time.sleep(0.2)
            task_log_f.close()
        thread = threading.Thread(target=func)
        thread.start()

    def disconnect(self, close_code):
        self.disconnected = True
        self.close()



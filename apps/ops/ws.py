import time
import threading

from .celery.utils import get_celery_task_log_path
from channels.generic.websocket import JsonWebsocketConsumer


class CeleryLogWebsocket(JsonWebsocketConsumer):
    task = ''
    task_log_f = None
    disconnected = False

    def connect(self):
        task_id = self.scope['url_route']['kwargs']['task_id']
        log_path = get_celery_task_log_path(task_id)
        try:
            self.task_log_f = open(log_path)
        except OSError:
            self.send({'message': "Task {} log not found".format(task_id)})
            self.disconnect(None)
            return

        self.accept()
        self.send_log_to_client()

    def disconnect(self, close_code):
        self.disconnected = True
        if self.task_log_f and not self.task_log_f.closed:
            self.task_log_f.close()
        self.close()

    def send_log_to_client(self):
        def func():
            while not self.disconnected:
                data = self.task_log_f.read(4096)
                if data:
                    data = data.replace('\n', '\r\n')
                    self.send_json({'message': data})
                time.sleep(0.2)
        thread = threading.Thread(target=func)
        thread.start()

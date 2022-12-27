import datetime

from channels.generic.websocket import JsonWebsocketConsumer
from django.utils import timezone
from rest_framework.renderers import JSONRenderer

from common.db.utils import safe_db_connection
from common.utils import get_logger
from terminal.serializers import TaskSerializer
from .signal_handlers import terminal_task_pub_sub

logger = get_logger(__name__)


class TerminalTaskWebsocket(JsonWebsocketConsumer):
    sub = None
    terminal = None

    def connect(self):
        user = self.scope["user"]
        if user.terminal:
            self.accept()
            self.terminal = user.terminal
            self.sub = self.watch_terminal_task_change()
        else:
            self.close()

    def receive_json(self, content, **kwargs):
        # todo: 暂时不处理, 可仅保持心跳
        pass

    def get_terminal_tasks(self):
        critical_time = timezone.now() - datetime.timedelta(minutes=10)
        tasks = self.terminal.task_set.filter(is_finished=False, date_created__gte=critical_time)
        serializer = TaskSerializer(tasks, many=True)
        return JSONRenderer().render(serializer.data)

    def send_terminal_task_msg(self):
        content = self.get_terminal_tasks()
        self.send(bytes_data=content)

    def watch_terminal_task_change(self):
        ws = self
        # 先发一次已有的任务
        with safe_db_connection():
            self.send_terminal_task_msg()

        def handle_terminal_task_msg_recv(msg):
            logger.debug('New terminal task msg recv: {}'.format(msg))
            ws.send_terminal_task_msg()

        return terminal_task_pub_sub.subscribe(handle_terminal_task_msg_recv)

    def disconnect(self, code):
        if self.sub:
            self.sub.unsubscribe()

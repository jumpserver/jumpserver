import datetime

from channels.generic.websocket import JsonWebsocketConsumer
from django.utils import timezone
from rest_framework.renderers import JSONRenderer

from common.db.utils import safe_db_connection
from common.utils import get_logger
from terminal.serializers import TaskSerializer
from .signal_handlers import component_event_chan

logger = get_logger(__name__)


class TerminalTaskWebsocket(JsonWebsocketConsumer):
    sub = None
    terminal = None

    def connect(self):
        user = self.scope["user"]
        if user.is_authenticated and user.terminal:
            self.accept()
            self.terminal = user.terminal
            self.sub = self.watch_component_event()
        else:
            self.close()

    def receive_json(self, content, **kwargs):
        # todo: 暂时不处理, 可仅保持心跳
        pass

    def get_terminal_tasks(self, task_id=None):
        with safe_db_connection():
            critical_time = timezone.now() - datetime.timedelta(minutes=10)
            tasks = self.terminal.task_set.filter(is_finished=False, date_created__gte=critical_time)
            if task_id:
                tasks = tasks.filter(id=task_id)
            serializer = TaskSerializer(tasks, many=True)
            return JSONRenderer().render(serializer.data)

    def send_kill_tasks_msg(self, task_id=None):
        content = self.get_terminal_tasks(task_id)
        self.send(bytes_data=content)

    def watch_component_event(self):
        ws = self
        # 先发一次已有的任务
        self.send_kill_tasks_msg()

        def handle_task_msg_recv(msg):
            logger.debug('New component task msg recv: {}'.format(msg))
            msg_type = msg.get('type')
            payload = msg.get('payload')
            if msg_type == "kill_session":
                ws.send_kill_tasks_msg(payload.get('id'))

        return component_event_chan.subscribe(handle_task_msg_recv)

    def disconnect(self, code):
        if self.sub:
            self.sub.unsubscribe()

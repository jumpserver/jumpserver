import datetime

from channels.generic.websocket import JsonWebsocketConsumer
from django.utils import timezone
from rest_framework.renderers import JSONRenderer

from common.db.utils import safe_db_connection
from common.utils import get_logger
from common.utils.connection import Subscription
from terminal.const import TaskNameType
from terminal.models import Session, Terminal
from terminal.serializers import TaskSerializer, StatSerializer
from .signal_handlers import component_event_chan

logger = get_logger(__name__)


class TerminalTaskWebsocket(JsonWebsocketConsumer):
    sub: Subscription = None
    terminal: Terminal = None

    def connect(self):
        user = self.scope["user"]
        if user.is_authenticated and user.terminal:
            self.accept()
            self.terminal = user.terminal
            self.sub = self.watch_component_event()
        else:
            self.close()

    def receive_json(self, content, **kwargs):
        req_type = content.get('type')
        if req_type == "status":
            payload = content.get('payload')
            self.handle_status(payload)

    def handle_status(self, content):
        serializer = StatSerializer(data=content)
        if not serializer.is_valid():
            logger.error('Invalid status data: {}'.format(serializer.errors))
            return
        serializer.validated_data["terminal"] = self.terminal
        session_ids = serializer.validated_data.pop('sessions', [])
        Session.set_sessions_active(session_ids)
        with safe_db_connection():
            serializer.save()

    def send_tasks_msg(self, task_id=None):
        content = self.get_terminal_tasks(task_id)
        self.send(bytes_data=content)

    def get_terminal_tasks(self, task_id=None):
        with safe_db_connection():
            critical_time = timezone.now() - datetime.timedelta(minutes=10)
            tasks = self.terminal.task_set.filter(is_finished=False, date_created__gte=critical_time)
            if task_id:
                tasks = tasks.filter(id=task_id)
            serializer = TaskSerializer(tasks, many=True)
            return JSONRenderer().render(serializer.data)

    def watch_component_event(self):
        # 先发一次已有的任务
        self.send_tasks_msg()

        ws = self

        def handle_task_msg_recv(msg):
            logger.debug('New component task msg recv: {}'.format(msg))
            msg_type = msg.get('type')
            payload = msg.get('payload')
            if msg_type in TaskNameType.names:
                ws.send_tasks_msg(payload.get('id'))

        return component_event_chan.subscribe(handle_task_msg_recv)

    def disconnect(self, code):
        if self.sub is None:
            return
        self.sub.unsubscribe()

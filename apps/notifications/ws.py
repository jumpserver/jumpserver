import threading
import json
from channels.generic.websocket import JsonWebsocketConsumer

from common.utils import get_logger
from common.db.utils import safe_db_connection
from .site_msg import SiteMessageUtil
from .signals_handler import NewSiteMsgSubPub

logger = get_logger(__name__)


class SiteMsgWebsocket(JsonWebsocketConsumer):
    refresh_every_seconds = 10

    def __init__(self, *args, **kwargs):
        super(SiteMsgWebsocket, self).__init__(*args, **kwargs)
        self.subscriber = None

    def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            self.accept()

            thread = threading.Thread(target=self.watch_recv_new_site_msg)
            thread.start()
        else:
            self.close()

    def disconnect(self, code):
        if self.subscriber:
            self.subscriber.close_handle_msg()

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = json.loads(text_data)
        refresh_every_seconds = data.get('refresh_every_seconds')

        try:
            refresh_every_seconds = int(refresh_every_seconds)
        except Exception as e:
            logger.error(e)
            return

        if refresh_every_seconds > 0:
            self.refresh_every_seconds = refresh_every_seconds

    def send_unread_msg_count(self):
        user_id = self.scope["user"].id
        unread_count = SiteMessageUtil.get_user_unread_msgs_count(user_id)
        logger.debug('Send unread count to user: {} {}'.format(user_id, unread_count))
        self.send_json({'type': 'unread_count', 'unread_count': unread_count})

    def watch_recv_new_site_msg(self):
        ws = self
        user_id = str(self.scope["user"].id)

        # 先发一个消息再说
        with safe_db_connection():
            self.send_unread_msg_count()

        def handle_new_site_msg_recv(msg):
            users = msg.get('users', [])
            logger.debug('New site msg recv, message users: {}'.format(users))
            if user_id in users:
                ws.send_unread_msg_count()

        subscriber = NewSiteMsgSubPub()
        self.subscriber = subscriber
        subscriber.keep_handle_msg(handle_new_site_msg_recv)

import json

from channels.generic.websocket import JsonWebsocketConsumer
from django.core.cache import caches

from common.db.utils import safe_db_connection
from common.utils import get_logger
from .signal_handlers import new_site_msg_chan
from .site_msg import SiteMessageUtil

logger = get_logger(__name__)
WS_SESSION_KEY = 'ws_session_key'


class SiteMsgWebsocket(JsonWebsocketConsumer):
    sub = None
    refresh_every_seconds = 10

    def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            self.accept()
            session = self.scope['session']
            caches.sadd(WS_SESSION_KEY, session.session_key)
            self.sub = self.watch_recv_new_site_msg()
        else:
            self.close()

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

        return new_site_msg_chan.subscribe(handle_new_site_msg_recv)

    def disconnect(self, code):
        if not self.sub:
            return
        self.sub.unsubscribe()
        session = self.scope['session']
        caches.srem(WS_SESSION_KEY, session.session_key)

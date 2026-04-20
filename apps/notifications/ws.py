import json

from channels.generic.websocket import JsonWebsocketConsumer

from common.db.utils import safe_db_connection
from common.utils import get_logger
from .signal_handlers import new_site_msg_chan
from .site_msg import SiteMessageUtil
from .models.site_msg import MessageContent

logger = get_logger(__name__)


class SiteMsgWebsocket(JsonWebsocketConsumer):
    sub = None
    refresh_every_seconds = 10

    @property
    def session(self):
        return self.scope['session']

    def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            self.accept()
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

    def send_unread_msg_count(self, user_id):
        unread_count = SiteMessageUtil.get_user_unread_msgs_count(user_id)
        logger.debug('Send unread count to user: {} {}'.format(user_id, unread_count))
        self.send_json({'type': 'unread_count', 'unread_count': unread_count})

    def send_site_msg_for_display(self, user_id):
        msgs = SiteMessageUtil.get_user_display_msgs(user_id)
        for msg in msgs:
            msg: MessageContent
            logger.debug('Send need display site msg to user: {} {} {}'.format(user_id, msg.id, msg.display_mode))
            msg_data = msg.as_data()
            self.send_json({'type': 'display', 'site_msg': msg_data})
    
    def send_site_msg(self):
        user_id = self.scope["user"].id
        self.send_unread_msg_count(user_id)
        self.send_site_msg_for_display(user_id)

    def watch_recv_new_site_msg(self):
        ws = self
        user_id = str(self.scope["user"].id)

        # 先发一个消息再说
        with safe_db_connection():
            self.send_site_msg()

        def handle_new_site_msg_recv(msg):
            users = msg.get('users', [])
            logger.debug('New site msg recv, message users: {}'.format(users))
            if user_id in users:
                ws.send_site_msg()

        return new_site_msg_chan.subscribe(handle_new_site_msg_recv)

    def disconnect(self, code):
        if not self.sub:
            return
        self.sub.unsubscribe()

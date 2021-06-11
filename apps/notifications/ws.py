import threading
import json

from channels.generic.websocket import JsonWebsocketConsumer

from common.utils import get_logger
from .models import SiteMessage
from .site_msg import SiteMessageUtil
from .signals_handler import new_site_msg_chan

logger = get_logger(__name__)


class SiteMsgWebsocket(JsonWebsocketConsumer):
    disconnected = False
    refresh_every_seconds = 10

    def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            self.accept()

            thread = threading.Thread(target=self.unread_site_msg_count)
            thread.start()
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

    def unread_site_msg_count(self):
        user_id = str(self.scope["user"].id)
        self.send_unread_msg_count()

        while not self.disconnected:
            subscribe = new_site_msg_chan.subscribe()
            for message in subscribe.listen():
                if message['type'] != 'message':
                    continue
                try:
                    msg = json.loads(message['data'].decode())
                    logger.debug('New site msg recv, may be mine: {}'.format(msg))
                    if not msg:
                        continue
                    users = msg.get('users', [])
                    logger.debug('Message users: {}'.format(users))
                    if user_id in users:
                        self.send_unread_msg_count()
                except json.JSONDecoder as e:
                    logger.debug('Decode json error: ', e)

    def disconnect(self, close_code):
        self.disconnected = True
        self.close()

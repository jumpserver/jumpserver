import time
import threading
import json

from common.utils import get_logger
from .site_msg import SiteMessage
from channels.generic.websocket import JsonWebsocketConsumer

logger = get_logger(__name__)


class UnreadSiteMsgCountWebsocket(JsonWebsocketConsumer):
    disconnected = False
    refresh_every_seconds = 5

    def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            self.accept()

            thread = threading.Thread(target=self.unread_sitemsg_count)
            thread.start()
        else:
            self.close()

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = json.loads(text_data)
        refresh_every_seconds = data.get('refresh_every_seconds')

        try:
            refresh_every_seconds = int(refresh_every_seconds)
        except:
            return

        if refresh_every_seconds > 0:
            self.refresh_every_seconds = refresh_every_seconds

    def unread_sitemsg_count(self):
        user_id = self.scope["user"].id

        while not self.disconnected:
            count = SiteMessage.get_user_unread_msgs_count(user_id)
            self.send_json({'unread_count': count})
            time.sleep(self.refresh_every_seconds)

    def disconnect(self, close_code):
        self.disconnected = True
        self.close()

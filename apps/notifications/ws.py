import json
import time
from threading import Thread

from channels.generic.websocket import JsonWebsocketConsumer
from django.conf import settings

from common.db.utils import safe_db_connection
from common.sessions.cache import user_session_manager
from common.utils import get_logger
from .signal_handlers import new_site_msg_chan
from .site_msg import SiteMessageUtil

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
            user_session_manager.add_or_increment(self.session.session_key)
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

        user_session_manager.decrement_or_remove(self.session.session_key)
        if self.should_delete_session():
            thread = Thread(target=self.delay_delete_session)
            thread.start()

    def should_delete_session(self):
        return (self.session.modified or settings.SESSION_SAVE_EVERY_REQUEST) and \
            not self.session.is_empty() and \
            self.session.get_expire_at_browser_close() and \
            not user_session_manager.check_active(self.session.session_key)

    def delay_delete_session(self):
        timeout = 6
        check_interval = 0.5

        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(check_interval)
            if user_session_manager.check_active(self.session.session_key):
                return

        self.delete_session()

    def delete_session(self):
        try:
            self.session.delete()
        except Exception as e:
            logger.info(f'delete session error: {e}')

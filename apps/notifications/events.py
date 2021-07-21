from functools import wraps
from common.utils.connection import RedisPubSub
from django.utils.functional import LazyObject


class UserEventSubPub(LazyObject):
    def _setup(self):
        self._wrapped = lambda: RedisPubSub('notifications.SiteMessageCome')


class Event:
    def __init__(self, user, tp, msg):
        self.user = user
        self.name = ''
        self.type = tp
        self.msg = msg


def on_user_event_ws_connect(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        event = func(*args, **kwargs)
        return event
    return wrapper


user_event_chan = UserEventSubPub()

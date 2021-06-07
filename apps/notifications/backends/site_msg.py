from notifications.site_msg import SiteMessage as Client, SITE_MSG_TYPE
from .base import BackendBase


class SiteMessage(BackendBase):
    account_field = 'id'

    def send_msg(self, users, subject, message):
        accounts, __, __ = self.get_accounts(users)
        Client.send_msg(subject, message, user_ids=accounts, type=SITE_MSG_TYPE.SYSTEM)

    @classmethod
    def is_enable(cls):
        return True

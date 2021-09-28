from notifications.site_msg import SiteMessageUtil as Client
from .base import BackendBase


class SiteMessage(BackendBase):
    account_field = 'id'

    def send_msg(self, users, message, subject):
        accounts, __, __ = self.get_accounts(users)
        Client.send_msg(subject, message, user_ids=accounts)

    @classmethod
    def is_enable(cls):
        return True


backend = SiteMessage

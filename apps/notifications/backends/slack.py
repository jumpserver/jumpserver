from django.conf import settings

from common.sdk.im.slack import Slack as Client
from .base import BackendBase


class Slack(BackendBase):
    account_field = 'slack_id'
    is_enable_field_in_settings = 'AUTH_SLACK'

    def __init__(self):
        self.client = Client(
            bot_token=settings.SLACK_BOT_TOKEN,
        )

    def send_msg(self, users, message, subject=None):
        accounts, __, __ = self.get_accounts(users)
        return self.client.send_text(accounts, message)


backend = Slack

from abc import ABCMeta

from django.conf import settings

from adapter import Client
from common.utils import get_logger

logger = get_logger(__name__)


class BasePam(object):
    __metaclass__ = ABCMeta

    header = {
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
        "content-type": "application/json;charset=utf-8"
    }

    def __init__(self):
        username = settings.PAM_USERNAME
        password = settings.PAM_PASSWORD
        self.client = self.login(username, password)

    def login(self, username, password):
        path = '/shterm/api/authenticate'
        data = dict(username=username, password=password)
        return Client(verify=False).adapter.post(path, headers=self.header, json=data)

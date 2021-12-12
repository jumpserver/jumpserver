from abc import ABCMeta

from ..adapter import Client
from ..adapter.exceptions import Unauthorized

from common.utils import get_logger

logger = get_logger(__name__)


# API 文档
# https://10.1.12.76/shterm/resources/docs/rest/index.html#api-Dev-PostDataBase


class BasePam(object):
    __metaclass__ = ABCMeta

    header = {
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
        "content-type": "application/json;charset=utf-8"
    }

    def __init__(self, url, username, password):
        self.client = Client(url=url, verify=False)
        self.is_active = True
        try:
            self.login(username, password)
        except Unauthorized:
            self.is_active = False
            logger.warning('Pam user authentication failed')

    def login(self, username, password):
        path = '/api/authenticate'
        data = dict(username=username, password=password)
        return self.client.adapter.post(path, headers=self.header, json=data)

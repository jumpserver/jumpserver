import urllib.parse

import requests
from django.conf import settings
from websockets.sync.client import connect as ws_connect


def get_loki_client():
    # TODO: 补充 auth 认证相关
    return LokiClient(base_url=settings.LOKI_BASE_URL)


# https://grafana.com/docs/loki/latest/reference/loki-http-api/

class LokiClient(object):
    query_range_url = '/loki/api/v1/query_range'
    tail_url = '/loki/api/v1/tail'

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def query_range(self, query, start, end, limit=100):
        params = {
            'query': query,
            'start': start,
            'end': end,
            'limit': limit,
        }
        url = f"{self.base_url}{self.query_range_url}"
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception(response.text)
        return response.json()

    def create_tail_ws(self, query, limit=100):
        data = {'query': query, 'limit': limit}
        params = urllib.parse.urlencode(data)
        ws_url = f"ws://{self.base_url[7:]}"
        if self.base_url.startswith('https://'):
            ws_url = f"wss://{self.base_url[8:]}"
        url = f"{ws_url}{self.tail_url}?{params}"
        ws = ws_connect(url)
        return LokiTailWs(ws)


class LokiTailWs(object):

    def __init__(self, ws):
        self._ws = ws

    def messages(self):
        for message in self._ws:
            yield message

    def close(self):
        if self._ws:
            self._ws.close()

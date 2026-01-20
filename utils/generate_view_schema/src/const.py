import os
from django.core.handlers.asgi import ASGIRequest


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE_DIR = os.path.join(os.path.join(CURRENT_DIR, 'output'))


# Fake Request object 尝试使用模拟请求
scope = {
    'type': 'http',
    'method': 'GET',
    'path': '/',
    'query_string': b'',
    'headers': [],
}

async def receive():
    return {'type': 'http.request', 'body': b''}

fake_request = ASGIRequest(scope, receive)


def log(message):
    print(message)
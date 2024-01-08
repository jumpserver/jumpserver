import mistune
import requests
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException

from common.utils.common import get_logger
from jumpserver.utils import get_current_request
from users.utils import construct_user_email

logger = get_logger(__name__)

SLACK_REDIRECT_URI_SESSION_KEY = '_slack_redirect_uri'


class URL:
    AUTHORIZE = 'https://slack.com/oauth/v2/authorize'
    ACCESS_TOKEN = 'https://slack.com/api/oauth.v2.access'
    GET_USER_INFO_BY_USER_ID = 'https://slack.com/api/users.info'
    SEND_MESSAGE = 'https://slack.com/api/chat.postMessage'
    AUTH_TEST = 'https://slack.com/api/auth.test'


class SlackRenderer(mistune.HTMLRenderer):
    def heading(self, text, level):
        return '*' + text + '*\n'

    def strong(self, text):
        return '*' + text + '*'

    def list(self, text, **kwargs):
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if not line:
                continue
            prefix = '• '
            lines[i] = prefix + line[4:-5]
        return '\n'.join(lines)

    def block_code(self, code, lang=None):
        return f'`{code}`'

    def link(self, link, text=None, title=None):
        if title or text:
            label = str(title or text).strip()
            return f'<{link}|{label}>'
        return f'<{link}>'

    def paragraph(self, text):
        return f'{text.strip()}\n'

    def linebreak(self):
        return '\n'


class SlackRequests:
    def __init__(self, client_id=None, client_secret=None, bot_token=None):
        self._client_id = client_id
        self._client_secret = client_secret
        self._bot_token = bot_token
        self.access_token = None
        self.user_id = None

    def add_token(self, headers, with_bot_token, with_access_token):
        if with_access_token:
            headers.update({'Authorization': f'Bearer {self.access_token}'})
        if with_bot_token:
            headers.update({'Authorization': f'Bearer {self._bot_token}'})

    def request(self, method, url, with_bot_token=True, with_access_token=False, **kwargs):
        headers = kwargs.pop('headers', {})
        self.add_token(headers, with_bot_token=with_bot_token, with_access_token=with_access_token)

        func_handler = getattr(requests, method, requests.get)
        data = func_handler(url, headers=headers, **kwargs).json()
        if not data.get('ok'):
            raise APIException(
                detail=data.get('error', _('Unknown error occur'))
            )
        return data

    def request_access_token(self, code):
        request = get_current_request()
        data = {
            'code': code, 'client_id': self._client_id, 'client_secret': self._client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': request.session.get(SLACK_REDIRECT_URI_SESSION_KEY)
        }
        response = self.request(
            'post', url=URL().ACCESS_TOKEN, data=data, with_bot_token=False
        )
        self.access_token = response['access_token']
        self.user_id = response['authed_user']['id']


class Slack:
    def __init__(self, client_id=None, client_secret=None, bot_token=None, **kwargs):
        self._client = SlackRequests(
            client_id=client_id, client_secret=client_secret, bot_token=bot_token
        )
        self.markdown = mistune.Markdown(renderer=SlackRenderer())

    def get_user_id_by_code(self, code):
        self._client.request_access_token(code)
        response = self._client.request(
            'get', f'{URL().GET_USER_INFO_BY_USER_ID}?user={self._client.user_id}',
            with_bot_token=False, with_access_token=True
        )
        return self._client.user_id, response['user']

    def is_valid(self):
        return self._client.request('post', URL().AUTH_TEST)

    def convert_to_markdown(self, message):
        blocks = []
        for line in message.split('\n'):
            block = self.markdown(line)
            if not block:
                continue
            if block.startswith('<hr>'):
                block_item = {'type': 'divider'}
            else:
                block_item = {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": block}
                }
            blocks.append(block_item)
        return {'blocks': blocks}

    def send_text(self, user_ids, msg_body):
        body = self.convert_to_markdown(msg_body)
        logger.info(f'Slack send text: user_ids={user_ids} msg={body}')
        for user_id in user_ids:
            body['channel'] = user_id
            try:
                self._client.request('post', URL().SEND_MESSAGE, json=body)
            except APIException as e:
                # 只处理可预知的错误
                logger.exception(e)

    @staticmethod
    def get_user_detail(user_id, **kwargs):
        # get_user_id_by_code 已经返回个人信息，这里直接解析
        user_info = kwargs['other_info']
        username = user_info.get('name') or user_id
        name = user_info.get('real_name', username)
        email = user_info.get('profile', {}).get('email')
        email = construct_user_email(username, email)
        return {
            'username': username, 'name': name, 'email': email
        }

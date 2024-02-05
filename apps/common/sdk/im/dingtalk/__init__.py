import base64
import hmac
import time

from common.sdk.im.mixin import BaseRequest
from common.sdk.im.utils import digest, as_request
from common.utils import get_logger
from users.utils import construct_user_email

logger = get_logger(__file__)


def sign(secret, data):

    digest = hmac.HMAC(
        key=secret.encode('utf8'),
        msg=data.encode('utf8'),
        digestmod=hmac._hashlib.sha256
    ).digest()
    signature = base64.standard_b64encode(digest).decode('utf8')
    # signature = urllib.parse.quote(signature, safe='')
    # signature = signature.replace('+', '%20').replace('*', '%2A').replace('~', '%7E').replace('/', '%2F')
    return signature


class ErrorCode:
    INVALID_TOKEN = 88


class URL:
    QR_CONNECT = 'https://login.dingtalk.com/oauth2/auth'
    OAUTH_CONNECT = 'https://oapi.dingtalk.com/connect/oauth2/sns_authorize'
    GET_USER_ACCESSTOKEN = 'https://api.dingtalk.com/v1.0/oauth2/userAccessToken'
    GET_USER_INFO = 'https://api.dingtalk.com/v1.0/contact/users/me'
    GET_TOKEN = 'https://oapi.dingtalk.com/gettoken'
    SEND_MESSAGE_BY_TEMPLATE = 'https://oapi.dingtalk.com/topapi/message/corpconversation/sendbytemplate'
    SEND_MESSAGE = 'https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2'
    GET_SEND_MSG_PROGRESS = 'https://oapi.dingtalk.com/topapi/message/corpconversation/getsendprogress'
    GET_USERID_BY_UNIONID = 'https://oapi.dingtalk.com/topapi/user/getbyunionid'
    GET_USER_INFO_BY_USER_ID = 'https://oapi.dingtalk.com/topapi/v2/user/get'


class DingTalkRequests(BaseRequest):
    invalid_token_errcodes = (ErrorCode.INVALID_TOKEN,)
    msg_key = 'errmsg'

    def __init__(self, appid, appsecret, agentid, timeout=None):
        self._appid = appid or ''
        self._appsecret = appsecret or ''
        self._agentid = agentid or ''

        super().__init__(timeout=timeout)

    def get_access_token_cache_key(self):
        return digest(self._appid, self._appsecret)

    def request_access_token(self):
        # https://developers.dingtalk.com/document/app/obtain-orgapp-token?spm=ding_open_doc.document.0.0.3a256573JEWqIL#topic-1936350
        params = {'appkey': self._appid, 'appsecret': self._appsecret}
        data = self.raw_request('get', url=URL.GET_TOKEN, params=params)

        access_token = data['access_token']
        expires_in = data['expires_in']
        return access_token, expires_in

    def add_token(self, kwargs: dict):
        params = kwargs.get('params')
        if params is None:
            params = {}
            kwargs['params'] = params
        params['access_token'] = self.access_token

    def get(self, url, params=None,
            with_token=False, with_sign=False,
            check_errcode_is_0=True,
            **kwargs) -> dict:
        pass

    get = as_request(get)

    def post(self, url, json=None, params=None,
             with_token=False, with_sign=False,
             check_errcode_is_0=True,
             **kwargs) -> dict:
        pass

    post = as_request(post)

    def _add_sign(self, kwargs: dict):
        params = kwargs.get('params')
        if params is None:
            params = {}
            kwargs['params'] = params

        timestamp = str(int(time.time() * 1000))
        signature = sign(self._appsecret, timestamp)

        params['timestamp'] = timestamp
        params['signature'] = signature
        params['accessKey'] = self._appid

    def request(self, method, url,
                with_token=False, with_sign=False,
                check_errcode_is_0=True,
                **kwargs):

        if with_sign:
            self._add_sign(kwargs)

        data = super().request(
            method, url, with_token=with_token,
            check_errcode_is_0=check_errcode_is_0, **kwargs
        )
        return data


class DingTalk:
    def __init__(self, appid, appsecret, agentid, timeout=None):
        self._appid = appid or ''
        self._appsecret = appsecret or ''
        self._agentid = agentid or ''

        self._request = DingTalkRequests(
            appid=appid, appsecret=appsecret, agentid=agentid,
            timeout=timeout
        )

    def get_userinfo_bycode(self, code):
        body = {
            'clientId': self._appid,
            'clientSecret': self._appsecret,
            'code': code,
            'grantType': 'authorization_code'
        }
        data = self._request.post(URL.GET_USER_ACCESSTOKEN, json=body, check_errcode_is_0=False)
        token = data['accessToken']

        user = self._request.get(URL.GET_USER_INFO,
                                 headers={'x-acs-dingtalk-access-token': token}, check_errcode_is_0=False)
        return user

    def get_user_id_by_code(self, code):
        user_info = self.get_userinfo_bycode(code)
        unionid = user_info['unionId']
        userid = self.get_userid_by_unionid(unionid)
        return userid, None

    def get_userid_by_unionid(self, unionid):
        body = {
            'unionid': unionid
        }
        data = self._request.post(URL.GET_USERID_BY_UNIONID, json=body, with_token=True)
        userid = data['result']['userid']
        return userid

    def send_by_template(self, template_id, user_ids, dept_ids, data):
        body = {
            'agent_id': self._agentid,
            'template_id': template_id,
            'userid_list': ','.join(user_ids),
            'dept_id_list': ','.join(dept_ids),
            'data': data
        }
        data = self._request.post(URL.SEND_MESSAGE_BY_TEMPLATE, json=body, with_token=True)
        return data

    def send_markdown(self, user_ids, title, msg):
        body = {
            'agent_id': self._agentid,
            'userid_list': ','.join(user_ids),
            'to_all_user': False,
            'msg': {
                'msgtype': 'markdown',
                'markdown': {
                    'title': title,
                    'text': msg
                }
            }
        }
        logger.info(f'Dingtalk send markdown to user {user_ids}: {msg}')
        data = self._request.post(URL.SEND_MESSAGE, json=body, with_token=True)
        return data

    def send_text(self, user_ids, msg):
        body = {
            'agent_id': self._agentid,
            'userid_list': ','.join(user_ids),
            'to_all_user': False,
            'msg': {
                'msgtype': 'text',
                'text': {
                    'content': msg
                }
            }
        }
        logger.info(f'Dingtalk send msg to user {user_ids}: {msg}')
        data = self._request.post(URL.SEND_MESSAGE, json=body, with_token=True)
        return data

    def get_send_msg_progress(self, task_id):
        body = {
            'agent_id': self._agentid,
            'task_id': task_id
        }

        data = self._request.post(URL.GET_SEND_MSG_PROGRESS, json=body, with_token=True)
        return data

    def get_user_detail(self, user_id, **kwargs):
        # https://open.dingtalk.com/document/orgapp/query-user-details
        body = {'userid': user_id}
        data = self._request.post(
            URL.GET_USER_INFO_BY_USER_ID, json=body, with_token=True
        )
        data = data['result']
        username = user_id
        name = data.get('name', username)
        email = data.get('email') or data.get('org_email')
        email = construct_user_email(username, email)
        return {
            'username': username, 'name': name, 'email': email
        }

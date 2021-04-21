import time
import hmac
import base64

from common.message.backends.utils import request
from common.message.backends.utils import digest
from common.message.backends.mixin import BaseRequest


def sign(secret, data):

    digest = hmac.HMAC(
        key=secret.encode('utf8'),
        msg=data.encode('utf8'),
        digestmod=hmac._hashlib.sha256).digest()
    signature = base64.standard_b64encode(digest).decode('utf8')
    # signature = urllib.parse.quote(signature, safe='')
    # signature = signature.replace('+', '%20').replace('*', '%2A').replace('~', '%7E').replace('/', '%2F')
    return signature


class ErrorCode:
    INVALID_TOKEN = 88


class URL:
    QR_CONNECT = 'https://oapi.dingtalk.com/connect/qrconnect'
    GET_USER_INFO_BY_CODE = 'https://oapi.dingtalk.com/sns/getuserinfo_bycode'
    GET_TOKEN = 'https://oapi.dingtalk.com/gettoken'


class DingTalkRequests(BaseRequest):
    invalid_token_errcode = ErrorCode.INVALID_TOKEN

    def __init__(self, appid, appsecret, agentid, timeout=None):
        self._appid = appid
        self._appsecret = appsecret
        self._agentid = agentid

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

    @request
    def get(self, url, params=None, with_token=False, with_sign=False, **kwargs):
        pass

    @request
    def post(self, url, json=None, params=None, with_token=False, with_sign=False, **kwargs):
        pass

    def _add_sign(self, params: dict):
        timestamp = str(int(time.time() * 1000))
        signature = sign(self._appsecret, timestamp)
        accessKey = self._appid

        params['timestamp'] = timestamp
        params['signature'] = signature
        params['accessKey'] = accessKey

    def request(self, method, url, params=None,
                with_token=False, with_sign=False,
                check_errcode_is_0=True,
                **kwargs):
        if not isinstance(params, dict):
            params = {}

        if with_token:
            params['access_token'] = self.access_token

        if with_sign:
            self._add_sign(params)

        data = self.raw_request(method, url, params=params, **kwargs)
        if check_errcode_is_0:
            self.check_errcode_is_0(data)

        return data


class DingTalk:
    def __init__(self, appid, appsecret, agentid, timeout=None):
        self._appid = appid
        self._appsecret = appsecret
        self._agentid = agentid

        self._request = DingTalkRequests(
            appid=appid, appsecret=appsecret, agentid=agentid,
            timeout=timeout
        )

    def get_userinfo_bycode(self, code):
        # https://developers.dingtalk.com/document/app/obtain-the-user-information-based-on-the-sns-temporary-authorization?spm=ding_open_doc.document.0.0.3a256573y8Y7yg#topic-1995619
        body = {
            "tmp_auth_code": code
        }

        data = self._request.post(URL.GET_USER_INFO_BY_CODE, json=body, with_sign=True)

        return data['user_info']['openid']


def test():
    from django.conf import settings

    req = DingTalkRequests(
        appid=settings.DINGTALK_APPKEY,
        appsecret=settings.DINGTALK_APPSECRET,
        agentid=settings.DINGTALK_AGENTID
    )

    return req


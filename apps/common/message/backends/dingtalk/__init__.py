import time
import hmac
import base64
from hashlib import sha256
import requests
import urllib

from django.core.cache import cache

from common.message.backends.utils import request
from common.message.backends.utils import digest


def sign(secret, data):
    # secret = secret.encode('utf8')
    # data = data.encode('utf8')
    # t = hmac.new(secret, data, digestmod=sha256).digest()
    # t1 = hmac.new(secret, data, digestmod=sha256).hexdigest().encode('utf8')
    # signature = base64.b64encode(t1)
    # signature = urllib.parse.quote(signature, safe='')

    digest = hmac.HMAC(
        key=secret.encode('utf8'),
        msg=data.encode('utf8'),
        digestmod=hmac._hashlib.sha256).digest()
    signature = base64.standard_b64encode(digest).decode('utf8')
    # signature = urllib.parse.quote(signature, safe='')
    # signature = signature.replace('+', '%20').replace('*', '%2A').replace('~', '%7E').replace('/', '%2F')
    return signature


class URL:
    QR_CONNECT = 'https://oapi.dingtalk.com/connect/qrconnect'
    GET_USER_INFO_BY_CODE = 'https://oapi.dingtalk.com/sns/getuserinfo_bycode'
    GET_TOKEN = 'https://oapi.dingtalk.com/gettoken'


class DingTalkRequests:
    """
    处理系统级错误，抛出 API 异常，直接生成 HTTP 响应，业务代码无需关心这些错误
    - 确保 status_code == 200
    - 确保 access_token 无效时重试
    """

    def __init__(self, appid, appsecret, agentid=None, timeout=None):
        self._request_kwargs = {
            'timeout': timeout
        }
        self._appid = appid
        self._appsecret = appsecret
        self._agentid = agentid
        self._set_access_token()

    def _set_access_token(self):
        self._access_token_cache_key = digest(self._appid, self._appsecret)

        access_token = cache.get(self._access_token_cache_key)
        if access_token:
            self._access_token = access_token
            return

        self._init_access_token()

    def _init_access_token(self):
        # 缓存中没有 access_token ，去企业微信请求
        params = {'appkey': self._appid, 'appsecret': self._appsecret}
        data = self.get(url=URL.GET_TOKEN, params=params)

        access_token = data['access_token']
        expires_in = data['expires_in']

        cache.set(self._access_token_cache_key, access_token, expires_in)
        self._access_token = access_token

    @request
    def get(self, url, params=None, with_token=False, with_sign=False, **kwargs):
        pass

    @request
    def post(self, url, data=None, json=None, params=None, with_token=False, with_sign=False, **kwargs):
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
                **kwargs):
        if not isinstance(params, dict):
            params = {}

        if with_sign:
            self._add_sign(params)

        if with_token:
            pass

        kwargs['params'] = params
        kwargs['url'] = url

        response = getattr(requests, method)(**kwargs)
        return response.json()


class DingTalk:
    def __init__(self, appid, appsecret, agentid=None, timeout=None):
        self._appid = appid
        self._appsecret = appsecret
        self._agentid = agentid

        self._request = DingTalkRequests(
            appid=appid, appsecret=appsecret, agentid=agentid,
            timeout=timeout
        )

    def get_user_info_by_code(self, code):
        # https://developers.dingtalk.com/document/app/obtain-the-user-information-based-on-the-sns-temporary-authorization?spm=ding_open_doc.document.0.0.3a256573y8Y7yg#topic-1995619
        body = {
            "tmp_auth_code": code
        }

        data = self._request.post(URL.GET_USER_INFO_BY_CODE, json=body)

        return data


def test():
    from django.conf import settings

    req = DingTalkRequests(
        appid=settings.DINGTALK_APPKEY,
        appsecret=settings.DINGTALK_APPSECRET,
        agentid=settings.DINGTALK_AGENTID
    )

    return req


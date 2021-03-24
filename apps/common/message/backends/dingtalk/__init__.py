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
    SEND_MESSAGE_BY_TEMPLATE = 'https://oapi.dingtalk.com/topapi/message/corpconversation/sendbytemplate'
    SEND_MESSAGE = 'https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2'
    GET_SEND_MSG_PROGRESS = 'https://oapi.dingtalk.com/topapi/message/corpconversation/getsendprogress'
    GET_USERID_BY_UNIONID = 'https://oapi.dingtalk.com/topapi/user/getbyunionid'


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
    def get(self, url, params=None,
            with_token=False, with_sign=False,
            check_errcode_is_0=True,
            **kwargs):
        pass

    @request
    def post(self, url, json=None, params=None,
             with_token=False, with_sign=False,
             check_errcode_is_0=True,
             **kwargs):
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
        return data['user_info']

    def get_userid_by_code(self, code):
        user_info = self.get_userinfo_bycode(code)
        unionid = user_info['unionid']
        userid = self.get_userid_by_unionid(unionid)
        return userid

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

    def send_text(self, user_ids, msg):
        body = {
            'agent_id': self._agentid,
            'userid_list': ','.join(user_ids),
            # 'dept_id_list': '',
            'to_all_user': False,
            'msg': {
                'msgtype': 'text',
                'text': {
                    'content': msg
                }
            }
        }
        data = self._request.post(URL.SEND_MESSAGE, json=body, with_token=True)
        return data

    def get_send_msg_progress(self, task_id):
        body = {
            'agent_id': self._agentid,
            'task_id': task_id
        }

        data = self._request.post(URL.GET_SEND_MSG_PROGRESS, json=body, with_token=True)
        return data

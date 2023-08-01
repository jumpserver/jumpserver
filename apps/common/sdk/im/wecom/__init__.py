from typing import Iterable, AnyStr

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException

from common.sdk.im.mixin import RequestMixin, BaseRequest
from common.sdk.im.utils import digest, update_values
from common.utils.common import get_logger
from users.utils import construct_user_email

logger = get_logger(__name__)


class WeComError(APIException):
    default_code = 'wecom_error'
    default_detail = _('WeCom error, please contact system administrator')


class URL:
    GET_TOKEN = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken'
    SEND_MESSAGE = 'https://qyapi.weixin.qq.com/cgi-bin/message/send'
    QR_CONNECT = 'https://login.work.weixin.qq.com/wwlogin/sso/login'
    OAUTH_CONNECT = 'https://open.weixin.qq.com/connect/oauth2/authorize'

    # https://open.work.weixin.qq.com/api/doc/90000/90135/91437
    GET_USER_ID_BY_CODE = 'https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo'
    GET_USER_DETAIL = 'https://qyapi.weixin.qq.com/cgi-bin/user/get'


class ErrorCode:
    # https://open.work.weixin.qq.com/api/doc/90000/90139/90313#%E9%94%99%E8%AF%AF%E7%A0%81%EF%BC%9A81013
    RECIPIENTS_INVALID = 81013  # UserID、部门ID、标签ID全部非法或无权限。

    # https: // open.work.weixin.qq.com / devtool / query?e = 82001
    RECIPIENTS_EMPTY = 82001  # 指定的成员/部门/标签全部为空

    # https://open.work.weixin.qq.com/api/doc/90000/90135/91437
    INVALID_CODE = 40029

    INVALID_TOKEN = 40014  # 无效的 access_token


class WeComRequests(BaseRequest):
    """
    处理系统级错误，抛出 API 异常，直接生成 HTTP 响应，业务代码无需关心这些错误
    - 确保 status_code == 200
    - 确保 access_token 无效时重试
    """
    invalid_token_errcodes = (ErrorCode.INVALID_TOKEN,)

    def __init__(self, corpid, corpsecret, agentid, timeout=None):
        self._corpid = corpid or ''
        self._corpsecret = corpsecret or ''
        self._agentid = agentid or ''

        super().__init__(timeout=timeout)

    def get_access_token_cache_key(self):
        return digest(self._corpid, self._corpsecret)

    def request_access_token(self):
        params = {'corpid': self._corpid, 'corpsecret': self._corpsecret}
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


class WeCom(RequestMixin):
    """
    非业务数据导致的错误直接抛异常，说明是系统配置错误，业务代码不用理会
    """

    def __init__(self, corpid, corpsecret, agentid, timeout=None):
        self._corpid = corpid or ''
        self._corpsecret = corpsecret or ''
        self._agentid = agentid or ''

        self._requests = WeComRequests(
            corpid=corpid,
            corpsecret=corpsecret,
            agentid=agentid,
            timeout=timeout
        )

    def send_markdown(self, users: Iterable, msg: AnyStr, **kwargs):
        pass

    def send_text(self, users: Iterable, msg: AnyStr, markdown=False, **kwargs):
        """
        https://open.work.weixin.qq.com/api/doc/90000/90135/90236

        对于业务代码，只需要关心由 用户id 或 消息不对 导致的错误，其他错误不予理会
        """
        users = tuple(users)

        extra_params = {
            "safe": 0,
            "enable_id_trans": 0,
            "enable_duplicate_check": 0,
            "duplicate_check_interval": 1800
        }
        update_values(extra_params, kwargs)

        body = {
            "touser": '|'.join(users),
            "msgtype": "text",
            "agentid": self._agentid,
            "text": {
                "content": msg
            },
            **extra_params
        }
        if markdown:
            body['msgtype'] = 'markdown'
            body["markdown"] = {
                "content": msg
            }
            body.pop('text', '')

        logger.info(f'Wecom send text: users={users} msg={msg}')
        data = self._requests.post(URL.SEND_MESSAGE, json=body, check_errcode_is_0=False)

        errcode = data['errcode']
        if errcode in (ErrorCode.RECIPIENTS_INVALID, ErrorCode.RECIPIENTS_EMPTY):
            # 全部接收人无权限或不存在
            return users
        self._requests.check_errcode_is_0(data)

        if 'invaliduser' not in data:
            return ()

        invaliduser = data['invaliduser']
        if not invaliduser:
            return ()

        if isinstance(invaliduser, str):
            logger.error(f'WeCom send text 200, but invaliduser is not str: invaliduser={invaliduser}')
            raise WeComError

        invalid_users = invaliduser.split('|')
        return invalid_users

    def get_user_id_by_code(self, code):
        # # https://open.work.weixin.qq.com/api/doc/90000/90135/91437
        params = {'code': code}
        data = self._requests.get(URL.GET_USER_ID_BY_CODE, params=params, check_errcode_is_0=False)

        errcode = data['errcode']
        if errcode == ErrorCode.INVALID_CODE:
            logger.warn(f'WeCom get_user_id_by_code invalid code: code={code}')
            return None, None

        self._requests.check_errcode_is_0(data)

        USER_ID = 'UserId'
        OPEN_ID = 'OpenId'

        if USER_ID in data:
            return data[USER_ID], USER_ID
        elif OPEN_ID in data:
            return data[OPEN_ID], OPEN_ID
        else:
            logger.error(f'WeCom response 200 but get field from json error: fields=UserId|OpenId')
            raise WeComError

    def get_user_detail(self, user_id, **kwargs):
        # https://open.work.weixin.qq.com/api/doc/90000/90135/90196
        params = {'userid': user_id}
        data = self._requests.get(URL.GET_USER_DETAIL, params)
        username = data.get('userid')
        name = data.get('name', username)
        email = data.get('email') or data.get('biz_mail')
        email = construct_user_email(username, email)
        return {
            'username': username, 'name': name, 'email': email
        }

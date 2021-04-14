from typing import Iterable, AnyStr
import inspect
from inspect import Parameter

from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import APIException
from requests.exceptions import ReadTimeout
import requests
from django.core.cache import cache
import hashlib

from common.utils.common import get_logger


logger = get_logger(__name__)


class NetError(APIException):
    default_code = 'net_error'
    default_detail = _('Network error, please contact system administrator')


class WeComError(APIException):
    default_code = 'wecom_error'
    default_detail = _('WeCom error, please contact system administrator')


class URL:
    GET_TOKEN = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken'
    SEND_MESSAGE = 'https://qyapi.weixin.qq.com/cgi-bin/message/send'
    QR_CONNECT = 'https://open.work.weixin.qq.com/wwopen/sso/qrConnect'

    # https://open.work.weixin.qq.com/api/doc/90000/90135/91437
    GET_USER_ID_BY_CODE = 'https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo'
    GET_USER_DETAIL = 'https://qyapi.weixin.qq.com/cgi-bin/user/get'


class ErrorCode:
    # https://open.work.weixin.qq.com/api/doc/90000/90139/90313#%E9%94%99%E8%AF%AF%E7%A0%81%EF%BC%9A81013
    RECIPIENTS_INVALID = 81013  # UserID、部门ID、标签ID全部非法或无权限。

    # https://open.work.weixin.qq.com/api/doc/90000/90135/91437
    INVALID_CODE = 40029

    INVALID_TOKEN = 40014  # 无效的 access_token


def update_values(default: dict, others: dict):
    for key in default.keys():
        if key in others:
            default[key] = others[key]


def set_default(data: dict, default: dict):
    for key in default.keys():
        if key not in data:
            data[key] = default[key]


def digest(corpid, corpsecret):
    md5 = hashlib.md5()
    md5.update(corpid.encode())
    md5.update(corpsecret.encode())
    digest = md5.hexdigest()
    return digest


class DictWrapper:
    def __init__(self, data:dict):
        self._dict = data

    def __getitem__(self, item):
        # 企业微信返回的数据，不能完全信任，所以字典操作包在异常里
        try:
            return self._dict[item]
        except KeyError as e:
            logger.error(f'WeCom response 200 but get field from json error: error={e}')
            raise WeComError

    def __getattr__(self, item):
        return getattr(self._dict, item)

    def __contains__(self, item):
        return item in self._dict


class WeComMixin:
    def check_errcode_is_0(self, data: DictWrapper):
        errcode = data['errcode']
        if errcode != 0:
            # 如果代码写的对，配置没问题，这里不该出错，系统性错误，直接抛异常
            errmsg = data['errmsg']
            logger.error(f'WeCom response 200 but errcode wrong: '
                         f'errcode={errcode} '
                         f'errmsg={errmsg} ')
            raise WeComError


def to_parameters(*exclude_fields):
    def wrapper(func):
        def inner(*args, **kwargs):
            signature = inspect.signature(func)
            bound_args = signature.bind(*args, **kwargs)
            bound_args.apply_defaults()
            if 'parameters' in kwargs:
                raise ValueError('You can not assign `parameters`')

            arguments = bound_args.arguments
            parameters = {}
            for k, v in signature.parameters.items():
                if k == 'self':
                    continue
                if k in exclude_fields:
                    continue
                if v.kind is Parameter.VAR_KEYWORD:
                    parameters.update(arguments[k])
                    continue
                parameters[k] = arguments[k]

            kwargs['parameters'] = parameters
            return func(*args, **kwargs)
        return inner
    return wrapper


def request(func):
    def inner(*args, **kwargs):
        signature = inspect.signature(func)
        bound_args = signature.bind(*args, **kwargs)
        bound_args.apply_defaults()

        arguments = bound_args.arguments
        self = arguments['self']
        request_method = func.__name__

        parameters = {}
        for k, v in signature.parameters.items():
            if k == 'self':
                continue
            if v.kind is Parameter.VAR_KEYWORD:
                parameters.update(arguments[k])
                continue
            parameters[k] = arguments[k]

        response = self.request(request_method, **parameters)
        return response
    return inner


class WeComRequests(WeComMixin):
    """
    处理系统级错误，抛出 API 异常，直接生成 HTTP 响应，业务代码无需关心这些错误
    - 确保 status_code == 200
    - 确保 access_token 无效时重试
    """

    def __init__(self, corpid, corpsecret, agentid, timeout=None):
        self._request_kwargs = {
            'timeout': timeout
        }
        self._corpid = corpid
        self._corpsecret = corpsecret
        self._agentid = agentid
        self._set_access_token()

    def _set_access_token(self):
        self._access_token_cache_key = digest(self._corpid, self._corpsecret)

        access_token = cache.get(self._access_token_cache_key)
        if access_token:
            self._access_token = access_token
            return

        self._init_access_token()

    def _init_access_token(self):
        # 缓存中没有 access_token ，去企业微信请求
        params = {'corpid': self._corpid, 'corpsecret': self._corpsecret}
        data = self.get(url=URL.GET_TOKEN, params=params, with_token=False)

        access_token = data['access_token']
        expires_in = data['expires_in']

        cache.set(self._access_token_cache_key, access_token, expires_in)
        self._access_token = access_token

    def _check_http_is_200(self, response):
        if response.status_code != 200:
            # 正常情况下不会返回非 200 响应码
            logger.error(f'Request WeCom error: '
                         f'status_code={response.status_code} '
                         f'\ncontent={response.content}')
            raise WeComError

    @request
    def get(self, url, params=None, with_token=True, with_agentid=False,
            check_errcode_is_0=True, **kwargs):
        # self.request ...
        pass

    @request
    def post(self, url, data=None, json=None, params=None,
             with_token=True, with_agentid=False, check_errcode_is_0=True,
             **kwargs):
        # self.request ...
        pass

    def request(self, method,
                params: dict = None,
                with_token=True,
                with_agentid=False,
                check_errcode_is_0=True,
                **kwargs):
        for i in range(3):
            # 循环为了防止 access_token 失效
            # https://open.work.weixin.qq.com/api/doc/90000/90135/91039
            try:
                if not isinstance(params, dict):
                    params = {}

                if with_token:
                    params['access_token'] = self._access_token

                if with_agentid:
                    params['agentid'] = self._agentid

                set_default(kwargs, self._request_kwargs)
                kwargs['params'] = params

                response = getattr(requests, method)(**kwargs)
                self._check_http_is_200(response)
                data = response.json()
                data = DictWrapper(data)

                errcode = data['errcode']
                if errcode == ErrorCode.INVALID_TOKEN:
                    self._init_access_token()
                    continue

                if check_errcode_is_0:
                    self.check_errcode_is_0(data)

                return data
            except ReadTimeout as e:
                logger.exception(e)
                raise NetError

        logger.error(f'WeCom access_token retry 3 times failed, check your config')
        raise WeComError


class WeCom(WeComMixin):
    """
    非业务数据导致的错误直接抛异常，说明是系统配置错误，业务代码不用理会
    """

    def __init__(self, corpid, corpsecret, agentid, timeout=None):
        self._corpid = corpid
        self._corpsecret = corpsecret
        self._agentid = agentid

        self._requests = WeComRequests(
            corpid=corpid,
            corpsecret=corpsecret,
            agentid=agentid,
            timeout=timeout
        )

    def send_text(self, users: Iterable, msg: AnyStr, **kwargs):
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
        params = {'access_token': self._access_token}
        data = self._requests.post(URL.SEND_MESSAGE, params=params, json=body, check_errcode_is_0=False)

        errcode = data['errcode']
        if errcode == ErrorCode.RECIPIENTS_INVALID:
            # 全部接收人无权限或不存在
            return users
        self.check_errcode_is_0(data)

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

        params = {
            'code': code,
        }
        data = self._requests.get(URL.GET_USER_ID_BY_CODE, params=params, check_errcode_is_0=False)

        errcode = data['errcode']
        if errcode == ErrorCode.INVALID_CODE:
            logger.warn(f'WeCom get_user_id_by_code invalid code: code={code}')
            return None, None

        self.check_errcode_is_0(data)

        USER_ID = 'UserId'
        OPEN_ID = 'OpenId'

        if USER_ID in data:
            return data[USER_ID], USER_ID
        elif OPEN_ID in data:
            return data[OPEN_ID], OPEN_ID
        else:
            logger.error(f'WeCom response 200 but get field from json error: fields=UserId|OpenId')
            raise WeComError

    def get_user_detail(self, id):
        # https://open.work.weixin.qq.com/api/doc/90000/90135/90196

        params = {
            'userid': id,
        }

        data = self._requests.get(URL.GET_USER_DETAIL, params)
        return data

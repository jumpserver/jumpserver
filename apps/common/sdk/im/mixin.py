import requests
from requests import exceptions as req_exce
from rest_framework.exceptions import PermissionDenied
from django.core.cache import cache

from .utils import DictWrapper
from common.utils.common import get_logger
from common.utils import lazyproperty
from common.sdk.im.utils import set_default, as_request

from . import exceptions as exce

logger = get_logger(__name__)


class RequestMixin:
    code_key: str
    msg_key: str


class BaseRequest(RequestMixin):
    """
    定义了 `access_token` 的过期刷新框架
    """
    invalid_token_errcodes = ()
    code_key = 'errcode'
    msg_key = 'err_msg'

    def __init__(self, timeout=None):
        self._request_kwargs = {
            'timeout': timeout
        }
        self.init_access_token()

    @classmethod
    def check_errcode_is_0(cls, data: DictWrapper):
        errcode = data[cls.code_key]
        if errcode != 0:
            # 如果代码写的对，配置没问题，这里不该出错，系统性错误，直接抛异常
            errmsg = data[cls.msg_key]
            logger.error(f'Response 200 but errcode is not 0: '
                         f'errcode={errcode} '
                         f'errmsg={errmsg} ')
            raise exce.ErrCodeNot0(detail=data.raw_data)

    @staticmethod
    def check_http_is_200(response):
        if response.status_code != 200:
            # 正常情况下不会返回非 200 响应码
            logger.error(f'Response error: '
                         f'status_code={response.status_code} '
                         f'url={response.url}'
                         f'\ncontent={response.content}')
            raise exce.HTTPNot200(detail=response.json())

    def request_access_token(self):
        """
        获取新的 `access_token` 的方法，子类需要实现
        """
        raise NotImplementedError

    def get_access_token_cache_key(self):
        """
        获取 `access_token` 的缓存 key， 子类需要实现
        """
        raise NotImplementedError

    def add_token(self, kwargs: dict):
        """
        添加 token ，子类需要实现
        """
        raise NotImplementedError

    def is_token_invalid(self, data):
        code = data[self.code_key]
        if code in self.invalid_token_errcodes:
            logger.error(f'OAuth token invalid: {data}')
            return True
        return False

    @lazyproperty
    def access_token_cache_key(self):
        return self.get_access_token_cache_key()

    def init_access_token(self):
        access_token = cache.get(self.access_token_cache_key)
        if access_token:
            self.access_token = access_token
            return
        self.refresh_access_token()

    def refresh_access_token(self):
        access_token, expires_in = self.request_access_token()
        self.access_token = access_token
        cache.set(self.access_token_cache_key, access_token, expires_in - 10)

    def raw_request(self, method, url, **kwargs):
        set_default(kwargs, self._request_kwargs)
        try:
            response = getattr(requests, method)(url, **kwargs)
            self.check_http_is_200(response)
            raw_data = response.json()
            data = DictWrapper(raw_data)

            return data
        except req_exce.ReadTimeout as e:
            logger.exception(e)
            raise exce.NetError

    def token_request(self, method, url, **kwargs):
        for i in range(3):
            # 循环为了防止 access_token 失效
            self.add_token(kwargs)
            data = self.raw_request(method, url, **kwargs)

            if self.is_token_invalid(data):
                self.refresh_access_token()
                continue

            return data
        logger.error(f'Get access_token error, check config: url={url} data={data.raw_data}')
        raise PermissionDenied(data.raw_data)

    def get(self, url, params=None, with_token=True,
            check_errcode_is_0=True, **kwargs):
        # self.request ...
        pass
    get = as_request(get)

    def post(self, url, params=None, json=None,
             with_token=True, check_errcode_is_0=True,
             **kwargs):
        # self.request ...
        pass
    post = as_request(post)

    def request(self, method, url,
                with_token=True,
                check_errcode_is_0=True,
                **kwargs):

        if with_token:
            data = self.token_request(method, url, **kwargs)
        else:
            data = self.raw_request(method, url, **kwargs)

        if check_errcode_is_0:
            self.check_errcode_is_0(data)
        return data

import requests
from requests import exceptions as req_exce
from rest_framework.exceptions import PermissionDenied
from django.core.cache import cache

from .utils import DictWrapper
from common.utils.common import get_logger
from common.utils import lazyproperty
from common.message.backends.utils import set_default

from . import exceptions as exce

logger = get_logger(__name__)


class RequestMixin:
    def check_errcode_is_0(self, data: DictWrapper):
        errcode = data['errcode']
        if errcode != 0:
            # 如果代码写的对，配置没问题，这里不该出错，系统性错误，直接抛异常
            errmsg = data['errmsg']
            logger.error(f'Response 200 but errcode is not 0: '
                         f'errcode={errcode} '
                         f'errmsg={errmsg} ')
            raise exce.ErrCodeNot0(detail=data.raw_data)

    def check_http_is_200(self, response):
        if response.status_code != 200:
            # 正常情况下不会返回非 200 响应码
            logger.error(f'Response error: '
                         f'status_code={response.status_code} '
                         f'url={response.url}'
                         f'\ncontent={response.content}')
            raise exce.HTTPNot200(detail=response.json())


class BaseRequest(RequestMixin):
    invalid_token_errcode = -1

    def __init__(self, timeout=None):
        self._request_kwargs = {
            'timeout': timeout
        }
        self.init_access_token()

    def request_access_token(self):
        raise NotImplementedError

    def get_access_token_cache_key(self):
        raise NotImplementedError

    def is_token_invalid(self, data):
        errcode = data['errcode']
        if errcode == self.invalid_token_errcode:
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
        cache.set(self.access_token_cache_key, access_token, expires_in)

    def raw_request(self, method, url, **kwargs):
        set_default(kwargs, self._request_kwargs)
        raw_data = ''
        for i in range(3):
            # 循环为了防止 access_token 失效
            try:
                response = getattr(requests, method)(url, **kwargs)
                self.check_http_is_200(response)
                raw_data = response.json()
                data = DictWrapper(raw_data)

                if self.is_token_invalid(data):
                    self.refresh_access_token()
                    continue

                return data
            except req_exce.ReadTimeout as e:
                logger.exception(e)
                raise exce.NetError
        logger.error(f'Get access_token error, check config: url={url} data={raw_data}')
        raise PermissionDenied(raw_data)

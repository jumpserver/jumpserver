import json

from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import APIException

from common.utils.common import get_logger
from common.sdk.im.utils import digest
from common.sdk.im.mixin import RequestMixin, BaseRequest

logger = get_logger(__name__)


class URL:
    AUTHEN = 'https://open.feishu.cn/open-apis/authen/v1/index'

    GET_TOKEN = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/'

    # https://open.feishu.cn/document/ukTMukTMukTM/uEDO4UjLxgDO14SM4gTN
    GET_USER_INFO_BY_CODE = 'https://open.feishu.cn/open-apis/authen/v1/access_token'

    SEND_MESSAGE = 'https://open.feishu.cn/open-apis/im/v1/messages'


class ErrorCode:
    INVALID_APP_ACCESS_TOKEN = 99991664
    INVALID_USER_ACCESS_TOKEN = 99991668
    INVALID_TENANT_ACCESS_TOKEN = 99991663


class FeishuRequests(BaseRequest):
    """
    处理系统级错误，抛出 API 异常，直接生成 HTTP 响应，业务代码无需关心这些错误
    - 确保 status_code == 200
    - 确保 access_token 无效时重试
    """
    invalid_token_errcodes = (
        ErrorCode.INVALID_USER_ACCESS_TOKEN, ErrorCode.INVALID_TENANT_ACCESS_TOKEN,
        ErrorCode.INVALID_APP_ACCESS_TOKEN
    )
    code_key = 'code'
    msg_key = 'msg'

    def __init__(self, app_id, app_secret, timeout=None):
        self._app_id = app_id
        self._app_secret = app_secret

        super().__init__(timeout=timeout)

    def get_access_token_cache_key(self):
        return digest(self._app_id, self._app_secret)

    def request_access_token(self):
        data = {'app_id': self._app_id, 'app_secret': self._app_secret}
        response = self.raw_request('post', url=URL.GET_TOKEN, data=data)
        self.check_errcode_is_0(response)

        access_token = response['tenant_access_token']
        expires_in = response['expire']
        return access_token, expires_in

    def add_token(self, kwargs: dict):
        headers = kwargs.setdefault('headers', {})
        headers['Authorization'] = f'Bearer {self.access_token}'


class FeiShu(RequestMixin):
    """
    非业务数据导致的错误直接抛异常，说明是系统配置错误，业务代码不用理会
    """

    def __init__(self, app_id, app_secret, timeout=None):
        self._app_id = app_id or ''
        self._app_secret = app_secret or ''

        self._requests = FeishuRequests(
            app_id=app_id,
            app_secret=app_secret,
            timeout=timeout
        )

    def get_user_id_by_code(self, code):
        # https://open.feishu.cn/document/ukTMukTMukTM/uEDO4UjLxgDO14SM4gTN

        body = {
            'grant_type': 'authorization_code',
            'code': code
        }

        data = self._requests.post(URL.GET_USER_INFO_BY_CODE, json=body, check_errcode_is_0=False)

        self._requests.check_errcode_is_0(data)
        return data['data']['user_id']

    def send_text(self, user_ids, msg):
        params = {
            'receive_id_type': 'user_id'
        }

        body = {
            'msg_type': 'text',
            'content': json.dumps({'text': msg})
        }

        invalid_users = []
        for user_id in user_ids:
            body['receive_id'] = user_id

            try:
                logger.info(f'Feishu send text: user_ids={user_ids} msg={msg}')
                self._requests.post(URL.SEND_MESSAGE, params=params, json=body)
            except APIException as e:
                # 只处理可预知的错误
                logger.exception(e)
                invalid_users.append(user_id)
        return invalid_users

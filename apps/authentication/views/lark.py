from django.utils.translation import gettext_lazy as _

from common.sdk.im.lark import URL
from common.utils import get_logger
from .feishu import (
    FeiShuEnableStartView, FeiShuQRBindView, FeiShuQRBindCallbackView,
    FeiShuQRLoginView, FeiShuQRLoginCallbackView
)

logger = get_logger(__file__)


class LarkEnableStartView(FeiShuEnableStartView):
    category = 'lark'


class BaseLarkQRMixin:
    category = 'lark'
    error = _('Lark Error')
    error_msg = _('Lark is already bound')
    state_session_key = f'_{category}_state'

    @property
    def url_object(self):
        return URL()


class LarkQRBindView(BaseLarkQRMixin, FeiShuQRBindView):
    pass


class LarkQRBindCallbackView(BaseLarkQRMixin, FeiShuQRBindCallbackView):
    auth_type = 'lark'
    auth_type_label = auth_type.capitalize()
    client_type_path = f'common.sdk.im.{auth_type}.Lark'


class LarkQRLoginView(BaseLarkQRMixin, FeiShuQRLoginView):
    pass


class LarkQRLoginCallbackView(BaseLarkQRMixin, FeiShuQRLoginCallbackView):
    user_type = 'lark'
    auth_type = user_type
    client_type_path = f'common.sdk.im.{auth_type}.Lark'

    msg_client_err = _('Lark Error')
    msg_user_not_bound_err = _('Lark is not bound')
    msg_not_found_user_from_client_err = _('Failed to get user from Lark')

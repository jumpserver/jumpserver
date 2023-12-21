from django.utils.translation import gettext_lazy as _
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication import errors
from authentication.const import ConfirmType
from authentication.permissions import UserConfirmation
from common.api import RoleUserMixin, RoleAdminMixin
from common.exceptions import JMSException
from common.permissions import IsValidUser, OnlySuperUser
from common.utils import get_logger
from users.models import User


logger = get_logger(__file__)


class QRUnBindBase(APIView):
    user: User

    def post(self, request: Request, backend: str, **kwargs):
        backend_map = {
            'wecom': {'user_field': 'wecom_id', 'not_bind_err': errors.WeComNotBound},
            'dingtalk': {'user_field': 'dingtalk_id', 'not_bind_err': errors.DingTalkNotBound},
            'feishu': {'user_field': 'feishu_id', 'not_bind_err': errors.FeiShuNotBound},
            'slack': {'user_field': 'slack_id', 'not_bind_err': errors.SlackNotBound},
        }
        user = self.user

        backend_info = backend_map.get(backend)
        if not backend_info:
            raise JMSException(
                _('The value in the parameter must contain %s') % ', '.join(backend_map.keys())
            )

        if not getattr(user, backend_info['user_field'], None):
            raise backend_info['not_bind_err']

        setattr(user, backend_info['user_field'], None)
        user.save()
        return Response()


class QRUnBindForUserApi(RoleUserMixin, QRUnBindBase):
    permission_classes = (IsValidUser, UserConfirmation.require(ConfirmType.RELOGIN),)


class QRUnBindForAdminApi(RoleAdminMixin, QRUnBindBase):
    permission_classes = (OnlySuperUser,)
    user_id_url_kwarg = 'user_id'

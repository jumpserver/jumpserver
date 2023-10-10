from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication import errors
from authentication.const import ConfirmType
from common.api import RoleUserMixin, RoleAdminMixin
from common.permissions import UserConfirmation, IsValidUser
from common.utils import get_logger
from users.models import User

logger = get_logger(__file__)


class WeComQRUnBindBase(APIView):
    user: User

    def post(self, request: Request, **kwargs):
        user = self.user

        if not user.wecom_id:
            raise errors.WeComNotBound

        user.wecom_id = None
        user.save()
        return Response()


class WeComQRUnBindForUserApi(RoleUserMixin, WeComQRUnBindBase):
    permission_classes = (IsValidUser, UserConfirmation.require(ConfirmType.RELOGIN),)


class WeComQRUnBindForAdminApi(RoleAdminMixin, WeComQRUnBindBase):
    user_id_url_kwarg = 'user_id'

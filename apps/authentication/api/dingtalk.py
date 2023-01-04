from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response

from users.models import User
from common.utils import get_logger
from common.permissions import UserConfirmation
from common.api import RoleUserMixin, RoleAdminMixin
from authentication.const import ConfirmType
from authentication import errors

logger = get_logger(__file__)


class DingTalkQRUnBindBase(APIView):
    user: User

    def post(self, request: Request, **kwargs):
        user = self.user

        if not user.dingtalk_id:
            raise errors.DingTalkNotBound

        user.dingtalk_id = None
        user.save()
        return Response()


class DingTalkQRUnBindForUserApi(RoleUserMixin, DingTalkQRUnBindBase):
    permission_classes = (UserConfirmation.require(ConfirmType.ReLogin),)


class DingTalkQRUnBindForAdminApi(RoleAdminMixin, DingTalkQRUnBindBase):
    user_id_url_kwarg = 'user_id'

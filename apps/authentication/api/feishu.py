from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication import errors
from authentication.const import ConfirmType
from authentication.permissions import UserConfirmation
from common.api import RoleUserMixin, RoleAdminMixin
from common.permissions import IsValidUser
from common.utils import get_logger
from users.models import User

logger = get_logger(__name__)


class FeiShuQRUnBindBase(APIView):
    user: User

    def post(self, request: Request, **kwargs):
        user = self.user

        if not user.feishu_id:
            raise errors.FeiShuNotBound

        user.feishu_id = None
        user.save()
        return Response()


class FeiShuQRUnBindForUserApi(RoleUserMixin, FeiShuQRUnBindBase):
    permission_classes = (IsValidUser, UserConfirmation.require(ConfirmType.RELOGIN),)


class FeiShuQRUnBindForAdminApi(RoleAdminMixin, FeiShuQRUnBindBase):
    user_id_url_kwarg = 'user_id'


class FeiShuEventSubscriptionCallback(APIView):
    """
    # https://open.feishu.cn/document/ukTMukTMukTM/uUTNz4SN1MjL1UzM
    """
    permission_classes = (IsValidUser,)

    def post(self, request: Request, *args, **kwargs):
        return Response(data=request.data)

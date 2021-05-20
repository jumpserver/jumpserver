from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response

from users.permissions import IsAuthPasswdTimeValid
from users.models import User
from common.utils import get_logger
from common.permissions import IsOrgAdmin
from common.mixins.api import RoleUserMixin, RoleAdminMixin
from authentication import errors

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
    permission_classes = (IsAuthPasswdTimeValid,)


class WeComQRUnBindForAdminApi(RoleAdminMixin, WeComQRUnBindBase):
    user_id_url_kwarg = 'user_id'
    permission_classes = (IsOrgAdmin,)

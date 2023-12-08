from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsValidUser
from common.utils import get_logger


logger = get_logger(__name__)


class FeiShuEventSubscriptionCallback(APIView):
    """
    # https://open.feishu.cn/document/ukTMukTMukTM/uUTNz4SN1MjL1UzM
    """
    permission_classes = (IsValidUser,)

    def post(self, request: Request, *args, **kwargs):
        return Response(data=request.data)

from .feishu import FeiShuTestingAPI
from .. import serializers


class LarkTestingAPI(FeiShuTestingAPI):
    category = 'LARK'
    serializer_class = serializers.LarkSettingSerializer

from common.utils.common import get_logger
from ..feishu import URL as FeiShuURL, FeishuRequests, FeiShu

logger = get_logger(__name__)


class URL(FeiShuURL):
    host = 'https://open.larksuite.com'


class LarkRequests(FeishuRequests):
    pass


class Lark(FeiShu):
    requests_cls = LarkRequests



class URL:
    QR_CONNECT = 'https://oapi.dingtalk.com/connect/qrconnect'


class DingTalkRequests:
    """
    处理系统级错误，抛出 API 异常，直接生成 HTTP 响应，业务代码无需关心这些错误
    - 确保 status_code == 200
    - 确保 access_token 无效时重试
    """

    def __init__(self, corpid, corpsecret, agentid, timeout=None):
        self._request_kwargs = {
            'timeout': timeout
        }
        self._corpid = corpid
        self._corpsecret = corpsecret
        self._agentid = agentid


from collections import OrderedDict

from django.conf import settings
from common.exceptions import JMSException
from common.utils import get_logger
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
# 导入对应产品模块的client models。
from tencentcloud.sms.v20210111 import sms_client, models
# 导入可选配置类
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

from .base import BaseSMSClient

logger = get_logger(__file__)


class TencentSMS(BaseSMSClient):
    """
    https://cloud.tencent.com/document/product/382/43196#.E5.8F.91.E9.80.81.E7.9F.AD.E4.BF.A1
    """
    SIGN_AND_TMPL_SETTING_FIELD_PREFIX = 'TENCENT'

    @classmethod
    def new_from_settings(cls):
        return cls(
            secret_id=settings.TENCENT_SECRET_ID,
            secret_key=settings.TENCENT_SECRET_KEY,
            sdkappid=settings.TENCENT_SDKAPPID
        )

    def __init__(self, secret_id: str, secret_key: str, sdkappid: str):
        self.sdkappid = sdkappid

        cred = credential.Credential(secret_id, secret_key)
        httpProfile = HttpProfile()
        httpProfile.reqMethod = "POST"  # post请求(默认为post请求)
        httpProfile.reqTimeout = 30    # 请求超时时间，单位为秒(默认60秒)
        httpProfile.endpoint = "sms.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.signMethod = "TC3-HMAC-SHA256"  # 指定签名算法
        clientProfile.language = "en-US"
        clientProfile.httpProfile = httpProfile
        self.client = sms_client.SmsClient(cred, "ap-guangzhou", clientProfile)

    def send_sms(self, phone_numbers: list, sign_name: str, template_code: str, template_param: OrderedDict, **kwargs):
        try:
            req = models.SendSmsRequest()
            # 基本类型的设置:
            # SDK采用的是指针风格指定参数，即使对于基本类型你也需要用指针来对参数赋值。
            # SDK提供对基本类型的指针引用封装函数
            # 帮助链接：
            # 短信控制台: https://console.cloud.tencent.com/smsv2
            # sms helper: https://cloud.tencent.com/document/product/382/3773

            # 短信应用ID: 短信SdkAppId在 [短信控制台] 添加应用后生成的实际SdkAppId，示例如1400006666
            req.SmsSdkAppId = self.sdkappid
            # 短信签名内容: 使用 UTF-8 编码，必须填写已审核通过的签名，签名信息可登录 [短信控制台] 查看
            req.SignName = sign_name
            # 短信码号扩展号: 默认未开通，如需开通请联系 [sms helper]
            req.ExtendCode = ""
            # 用户的 session 内容: 可以携带用户侧 ID 等上下文信息，server 会原样返回
            req.SessionContext = "Jumpserver"
            # 国际/港澳台短信 senderid: 国内短信填空，默认未开通，如需开通请联系 [sms helper]
            req.SenderId = ""
            # 下发手机号码，采用 E.164 标准，+[国家或地区码][手机号]
            # 示例如：+8613711112222， 其中前面有一个+号 ，86为国家码，13711112222为手机号，最多不要超过200个手机号
            req.PhoneNumberSet = phone_numbers
            # 模板 ID: 必须填写已审核通过的模板 ID。模板ID可登录 [短信控制台] 查看
            req.TemplateId = template_code
            # 模板参数: 若无模板参数，则设置为空
            req.TemplateParamSet = list(template_param.values())
            # 通过client对象调用DescribeInstances方法发起请求。注意请求方法名与请求对象是对应的。
            # 返回的resp是一个DescribeInstancesResponse类的实例，与请求对象对应。
            logger.info(f'Tencent sms send: '
                        f'phone_numbers={phone_numbers} '
                        f'sign_name={sign_name} '
                        f'template_code={template_code} '
                        f'template_param={template_param}')

            resp = self.client.SendSms(req)

            try:
                code = resp.SendStatusSet[0].Code
                msg = resp.SendStatusSet[0].Message
            except IndexError:
                raise JMSException(code='response_bad', detail=resp)

            if code.lower() != 'ok':
                raise JMSException(code=code, detail=msg)

            return resp
        except TencentCloudSDKException as e:
            raise JMSException(code=e.code, detail=e.message)


client = TencentSMS

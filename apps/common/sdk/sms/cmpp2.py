import hashlib
import socket
import struct
import time

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from common.exceptions import JMSException
from common.utils import get_logger
from .base import BaseSMSClient

logger = get_logger(__file__)

CMPP_CONNECT = 0x00000001  # 请求连接
CMPP_CONNECT_RESP = 0x80000001  # 请求连接应答
CMPP_TERMINATE = 0x00000002  # 终止连接
CMPP_TERMINATE_RESP = 0x80000002  # 终止连接应答
CMPP_SUBMIT = 0x00000004  # 提交短信
CMPP_SUBMIT_RESP = 0x80000004  # 提交短信应答
CMPP_DELIVER = 0x00000005  # 短信下发
CMPP_DELIVER_RESP = 0x80000005  # 下发短信应答


class CMPPBaseRequestInstance(object):
    def __init__(self):
        self.command_id = ''
        self.body = b''
        self.length = 0

    def get_header(self, sequence_id):
        length = struct.pack('!L', 12 + self.length)
        command_id = struct.pack('!L', self.command_id)
        sequence_id = struct.pack('!L', sequence_id)
        return length + command_id + sequence_id

    def get_message(self, sequence_id):
        return self.get_header(sequence_id) + self.body


class CMPPConnectRequestInstance(CMPPBaseRequestInstance):
    def __init__(self, sp_id, sp_secret):
        if len(sp_id) != 6:
            raise ValueError(_("sp_id is 6 bits"))

        super().__init__()

        source_addr = sp_id.encode('utf-8')
        sp_secret = sp_secret.encode('utf-8')
        version = struct.pack('!B', 0x02)
        timestamp = struct.pack('!L', int(self.get_now()))
        authenticator_source = source_addr + 9 * b'\x00' + sp_secret + self.get_now().encode('utf-8')
        auth_source_md5 = hashlib.md5(authenticator_source).digest()
        self.body = source_addr + auth_source_md5 + version + timestamp
        self.length = len(self.body)
        self.command_id = CMPP_CONNECT

    @staticmethod
    def get_now():
        return time.strftime('%m%d%H%M%S', time.localtime(time.time()))


class CMPPSubmitRequestInstance(CMPPBaseRequestInstance):
    def __init__(self, msg_src, dest_terminal_id, msg_content, src_id,
                 service_id='', dest_usr_tl=1):
        if len(msg_content) >= 70:
            raise JMSException('The message length should be within 70 characters')
        if len(dest_terminal_id) > 100:
            raise JMSException('The number of users receiving information should be less than 100')

        super().__init__()

        msg_id = 8 * b'\x00'
        pk_total = struct.pack('!B', 1)
        pk_number = struct.pack('!B', 1)
        registered_delivery = struct.pack('!B', 0)
        msg_level = struct.pack('!B', 0)
        service_id = ((10 - len(service_id)) * '\x00' + service_id).encode('utf-8')
        fee_user_type = struct.pack('!B', 2)
        fee_terminal_id = ('0' * 21).encode('utf-8')
        tp_pid = struct.pack('!B', 0)
        tp_udhi = struct.pack('!B', 0)
        msg_fmt = struct.pack('!B', 8)
        fee_type = '01'.encode('utf-8')
        fee_code = '000000'.encode('utf-8')
        valid_time = ('\x00' * 17).encode('utf-8')
        at_time = ('\x00' * 17).encode('utf-8')
        src_id = ((21 - len(src_id)) * '\x00' + src_id).encode('utf-8')
        reserve = b'\x00' * 8
        _msg_length = struct.pack('!B', len(msg_content) * 2)
        _msg_src = msg_src.encode('utf-8')
        _dest_usr_tl = struct.pack('!B', dest_usr_tl)
        _msg_content = msg_content.encode('utf-16-be')
        _dest_terminal_id = b''.join([
            (i + (21 - len(i)) * '\x00').encode('utf-8') for i in dest_terminal_id
        ])
        self.length = 126 + 21 * dest_usr_tl + len(_msg_content)
        self.command_id = CMPP_SUBMIT
        self.body = msg_id + pk_total + pk_number + registered_delivery \
                    + msg_level + service_id + fee_user_type + fee_terminal_id \
                    + tp_pid + tp_udhi + msg_fmt + _msg_src + fee_type + fee_code \
                    + valid_time + at_time + src_id + _dest_usr_tl + _dest_terminal_id \
                    + _msg_length + _msg_content + reserve


class CMPPTerminateRequestInstance(CMPPBaseRequestInstance):
    def __init__(self):
        super().__init__()
        self.body = b''
        self.command_id = CMPP_TERMINATE


class CMPPDeliverRespRequestInstance(CMPPBaseRequestInstance):
    def __init__(self, msg_id, result=0):
        super().__init__()
        msg_id = struct.pack('!Q', msg_id)
        result = struct.pack('!B', result)
        self.length = len(self.body)
        self.body = msg_id + result


class CMPPResponseInstance(object):
    def __init__(self):
        self.command_id = None
        self.length = None
        self.response_handler_map = {
            CMPP_CONNECT_RESP: self.connect_response_parse,
            CMPP_SUBMIT_RESP: self.submit_response_parse,
            CMPP_DELIVER: self.deliver_request_parse,
        }

    @staticmethod
    def connect_response_parse(body):
        status, = struct.unpack('!B', body[0:1])
        authenticator_ISMG = body[1:17]
        version, = struct.unpack('!B', body[17:18])
        return {
            'Status': status,
            'AuthenticatorISMG': authenticator_ISMG,
            'Version': version
        }

    @staticmethod
    def submit_response_parse(body):
        msg_id = body[:8]
        result = struct.unpack('!B', body[8:9])
        return {
            'Msg_Id': msg_id, 'Result': result[0]
        }

    @staticmethod
    def deliver_request_parse(body):
        msg_id, = struct.unpack('!Q', body[0:8])
        dest_id = body[8:29]
        service_id = body[29:39]
        tp_pid = struct.unpack('!B', body[39:40])
        tp_udhi = struct.unpack('!B', body[40:41])
        msg_fmt = struct.unpack('!B', body[41:42])
        src_terminal_id = body[42:63]
        registered_delivery = struct.unpack('!B', body[63:64])
        msg_length = struct.unpack('!B', body[64:65])
        msg_content = body[65:msg_length[0] + 65]
        return {
            'Msg_Id': msg_id, 'Dest_Id': dest_id, 'Service_Id': service_id,
            'TP_pid': tp_pid, 'TP_udhi': tp_udhi, 'Msg_Fmt': msg_fmt,
            'Src_terminal_Id': src_terminal_id, 'Registered_Delivery': registered_delivery,
            'Msg_Length': msg_length, 'Msg_content': msg_content
        }

    def parse_header(self, data):
        self.command_id, = struct.unpack('!L', data[4:8])
        sequence_id, = struct.unpack('!L', data[8:12])
        return {
            'length': self.length,
            'command_id': hex(self.command_id),
            'sequence_id': sequence_id
        }

    def parse_body(self, body):
        response_body_func = self.response_handler_map.get(self.command_id)
        if response_body_func is None:
            raise JMSException('Unable to parse the returned result: %s' % body)
        return response_body_func(body)

    def parse(self, data):
        self.length, = struct.unpack('!L', data[0:4])
        header = self.parse_header(data)
        body = self.parse_body(data[12:self.length])
        return header, body


class CMPPClient(object):
    def __init__(self, host, port, sp_id, sp_secret, src_id, service_id):
        self.ip = host
        self.port = port
        self.sp_id = sp_id
        self.sp_secret = sp_secret
        self.src_id = src_id
        self.service_id = service_id
        self._sequence_id = 0
        self._is_connect = False
        self._times = 3
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._connect()

    @property
    def sequence_id(self):
        s = self._sequence_id
        self._sequence_id += 1
        return s

    def _connect(self):
        self.__socket.settimeout(5)
        error_msg = _('Failed to connect to the CMPP gateway server, err: {}')
        for i in range(self._times):
            try:
                self.__socket.connect((self.ip, self.port))
            except Exception as err:
                error_msg = error_msg.format(str(err))
                logger.warning(error_msg)
                time.sleep(1)
            else:
                self._is_connect = True
                break
        else:
            raise JMSException(error_msg)

    def send(self, instance):
        if isinstance(instance, CMPPBaseRequestInstance):
            message = instance.get_message(sequence_id=self.sequence_id)
        else:
            message = instance
        self.__socket.send(message)

    def recv(self):
        raw_length = self.__socket.recv(4)
        length, = struct.unpack('!L', raw_length)
        header, body = CMPPResponseInstance().parse(
            raw_length + self.__socket.recv(length - 4)
        )
        return header, body

    def close(self):
        if self._is_connect:
            terminate_request = CMPPTerminateRequestInstance()
            self.send(terminate_request)
            self.__socket.close()

    def _cmpp_connect(self):
        connect_request = CMPPConnectRequestInstance(self.sp_id, self.sp_secret)
        self.send(connect_request)
        header, body = self.recv()
        if body['Status'] != 0:
            raise JMSException('CMPPv2.0 authentication failed: %s' % body)

    def _cmpp_send_sms(self, dest, sign_name, template_code, template_param):
        """
        优先发送template_param中message的信息
        若该内容不存在，则根据template_code构建验证码发送
        """
        message = template_param.get('message')
        if message is None:
            code = template_param.get('code')
            message = template_code.replace('{code}', code)
        msg = '【%s】 %s' % (sign_name, message)
        submit_request = CMPPSubmitRequestInstance(
            msg_src=self.sp_id, src_id=self.src_id, msg_content=msg,
            dest_usr_tl=len(dest), dest_terminal_id=dest,
            service_id=self.service_id
        )
        self.send(submit_request)
        header, body = self.recv()
        command_id = header.get('command_id')
        if command_id == CMPP_DELIVER:
            deliver_request = CMPPDeliverRespRequestInstance(
                msg_id=body['Msg_Id'], result=body['Result']
            )
            self.send(deliver_request)

    def send_sms(self, dest, sign_name, template_code, template_param):
        try:
            self._cmpp_connect()
            self._cmpp_send_sms(dest, sign_name, template_code, template_param)
        except Exception as e:
            logger.error('CMPPv2.0 Error: %s', e)
            self.close()
            raise JMSException(e)


class CMPP2SMS(BaseSMSClient):
    SIGN_AND_TMPL_SETTING_FIELD_PREFIX = 'CMPP2'

    @classmethod
    def new_from_settings(cls):
        return cls(
            host=settings.CMPP2_HOST, port=settings.CMPP2_PORT,
            sp_id=settings.CMPP2_SP_ID, sp_secret=settings.CMPP2_SP_SECRET,
            service_id=settings.CMPP2_SERVICE_ID, src_id=getattr(settings, 'CMPP2_SRC_ID', ''),
        )

    def __init__(self, host: str, port: int, sp_id: str, sp_secret: str, service_id: str, src_id=''):
        try:
            self.client = CMPPClient(
                host=host, port=port, sp_id=sp_id, sp_secret=sp_secret, src_id=src_id, service_id=service_id
            )
        except Exception as err:
            self.client = None
            logger.warning(err)
            raise JMSException(err)

    @staticmethod
    def need_pre_check():
        return False

    def send_sms(self, phone_numbers: list, sign_name: str, template_code: str, template_param: dict, **kwargs):
        try:
            logger.info(f'CMPPv2.0 sms send: '
                        f'phone_numbers={phone_numbers} '
                        f'sign_name={sign_name} '
                        f'template_code={template_code} '
                        f'template_param={template_param}')
            self.client.send_sms(phone_numbers, sign_name, template_code, template_param)
        except Exception as e:
            raise JMSException(e)


client = CMPP2SMS

import hashlib
import inspect
from inspect import Parameter

from common.utils.common import get_logger
from common.message.backends import exceptions as exce

logger = get_logger(__name__)


def digest(corpid, corpsecret):
    md5 = hashlib.md5()
    md5.update(corpid.encode())
    md5.update(corpsecret.encode())
    digest = md5.hexdigest()
    return digest


def update_values(default: dict, others: dict):
    for key in default.keys():
        if key in others:
            default[key] = others[key]


def set_default(data: dict, default: dict):
    for key in default.keys():
        if key not in data:
            data[key] = default[key]


class DictWrapper:
    def __init__(self, data:dict):
        self.raw_data = data

    def __getitem__(self, item):
        # 网络请求返回的数据，不能完全信任，所以字典操作包在异常里
        try:
            return self.raw_data[item]
        except KeyError as e:
            msg = f'Response 200 but get field from json error: error={e} data={self.raw_data}'
            logger.error(msg)
            raise exce.ResponseDataKeyError(detail=self.raw_data)

    def __getattr__(self, item):
        return getattr(self.raw_data, item)

    def __contains__(self, item):
        return item in self.raw_data

    def __str__(self):
        return str(self.raw_data)

    def __repr__(self):
        return str(self.raw_data)


def request(func):
    def inner(*args, **kwargs):
        signature = inspect.signature(func)
        bound_args = signature.bind(*args, **kwargs)
        bound_args.apply_defaults()

        arguments = bound_args.arguments
        self = arguments['self']
        request_method = func.__name__

        parameters = {}
        for k, v in signature.parameters.items():
            if k == 'self':
                continue
            if v.kind is Parameter.VAR_KEYWORD:
                parameters.update(arguments[k])
                continue
            parameters[k] = arguments[k]

        response = self.request(request_method, **parameters)
        return response
    return inner

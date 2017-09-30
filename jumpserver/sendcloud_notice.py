# coding: utf-8

import hashlib
import os

import requests

from settings import config, BASE_DIR

config.read(os.path.join(BASE_DIR, 'jumpserver.conf'))

accessKey = config.read('sendcloud', 'access_key')
secretKey = config.read('sendcloud', 'secret_key')

mail_url = 'http://api.notice.sendcloud.net/mailapi/send'


def _signature(param):
    param_keys = list(param.keys())
    param_keys.sort()

    param_str = ''

    for key in param_keys:
        param_str += key + '=' + str(param[key]) + '&'

    param_str = param_str[:-1]

    sign_str = secretKey + '&' + param_str + '&' + secretKey
    signature = hashlib.md5(sign_str).hexdigest()

    return signature


def send_mail(title, msg, mail_from=None, email_to=None, fail_silently=True):
    send(title, msg, email_to[0])
    pass


def send(title, msg, email_to):
    param = {
        'nickNames': ';'.join(email_to),
        'accessKey': accessKey,
        'subject': title,
        'content': msg,
    }

    param['signature'] = _signature(param)

    r = requests.get(mail_url, params=param)
    return r.status_code == 200

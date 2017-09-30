# coding: utf-8

import hashlib

import requests

from settings import SENDCLOUD_ACCESS_KEY, SENDCLOUD_SECRET_KEY

accessKey = SENDCLOUD_ACCESS_KEY
secretKey = SENDCLOUD_SECRET_KEY

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

    try:
        result = r.json()
        print("sendcloud:", result)
    except Exception, ex:
        print("sendcloud:ex:", ex, param)

    return result['statusCode'] == 200

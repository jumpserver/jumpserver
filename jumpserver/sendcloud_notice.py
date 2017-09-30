# coding: utf-8

import hashlib

import requests

from settings import SENDCLOUD_ACCESS_KEY, SENDCLOUD_SECRET_KEY

accessKey = SENDCLOUD_ACCESS_KEY
secretKey = SENDCLOUD_SECRET_KEY


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


def add_notice_user(mail):
    param = {
        'nickName': mail,
        'email': mail
    }
    return call_sendcloud_api('/linkmanMember/add', param)


def update_user(mail):
    param = {
        'nickName': mail,
        'email': mail
    }
    return call_sendcloud_api('/linkmanMember/modify', param)


def call_sendcloud_api(path, param):
    """
    调用 sendcloud 通知
    :param path:
    :param param:
    :return:
    """

    param['accessKey'] = accessKey

    param['signature'] = _signature(param)

    url = 'http://api.notice.sendcloud.net' + ('' if path.startswith('/') else '/') + path

    response = requests.get(url, params=param)

    try:
        result = response.json()
        print("sendcloud:", result, param)
    except Exception, ex:
        print("sendcloud:ex:", ex)

    return result['statusCode'] == 200


def send_mail(title, msg, mail_from=None, email_to=None, fail_silently=True):
    """
    发送邮件
    :param title:
    :param msg:
    :param mail_from:
    :param email_to:
    :param fail_silently:
    :return:
    """
    param = {
        'nickNames': ';'.join(email_to),
        'subject': title,
        'content': msg,
    }

    return call_sendcloud_api('/mailapi/send', param)

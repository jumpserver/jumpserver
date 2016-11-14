# ~*~ coding: utf-8 ~*~
#

from __future__ import unicode_literals
import requests
import ipaddress

from .models import LoginLog


def validate_ip(ip):
    try:
        ipaddress.ip_address(ip.decode('utf-8'))
        return True
    except ValueError:
        print('valid error')
    return False


def write_login_log(username, name='', login_type='W',
                    terminal='', login_ip='', user_agent=''):
    if not (login_ip and validate_ip(login_ip)):
        login_ip = '0.0.0.0'
    if not name:
        name = username
    login_city = get_ip_city(login_ip)
    LoginLog.objects.create(username=username, name=name, login_type=login_type, login_ip=login_ip,
                            terminal=terminal, login_city=login_city, user_agent=user_agent)


def get_ip_city(ip, timeout=10):
    # Taobao ip api: http://ip.taobao.com//service/getIpInfo.php?ip=8.8.8.8
    # Sina ip api: http://int.dpool.sina.com.cn/iplookup/iplookup.php?ip=8.8.8.8&format=js

    url = 'http://ip.taobao.com/service/getIpInfo.php?ip=' + ip
    r = requests.get(url, timeout=timeout)
    city = 'Unknown'
    if r.status_code == 200:
        try:
            data = r.json()
            if data['code'] == 0:
                city = data['data']['country'] + data['data']['city']
        except ValueError:
            pass
    return city



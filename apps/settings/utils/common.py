# coding: utf-8
from jumpserver.context_processor import default_interface
from django.conf import settings
from IPy import IP


def get_interface_setting_or_default():
    if not settings.XPACK_ENABLED:
        return default_interface
    from xpack.plugins.interface.models import Interface
    return Interface.get_interface_setting()


def get_login_title():
    return get_interface_setting_or_default()['login_title']


def generate_ips(ip_string):
    # 支持的格式
    # 192.168.1.1,192.168.1.2
    # 192.168.1.1-12 | 192.168.1.1-192.168.1.12 | 192.168.1.0/30 | 192.168.1.1
    ips = []
    ip_list = ip_string.split(',')
    if len(ip_list) > 1:
        for ip in ip_list:
            try:
                ips.append(str(IP(ip)))
            except ValueError:
                pass
        return ips

    ip_list = ip_string.split('-')
    try:
        if len(ip_list) == 2:
            start_ip, end_ip = ip_list
            if ip_list[1].find('.') == -1:
                end_ip = start_ip[:start_ip.rindex('.') + 1] + end_ip
            for ip in range(IP(start_ip).int(), IP(end_ip).int() + 1):
                ips.extend((str(ip) for ip in IP(ip)))
        else:
            ips.extend((str(ip) for ip in IP(ip_list[0])))
    except ValueError:
        ips = []
    return ips


def is_valid_port(port):
    valid = True
    try:
        port = int(port)
        if port > 65535 or port < 1:
            valid = False
    except (TypeError, ValueError):
        valid = False
    return valid

def generate_ports(ports):
    port_list = []
    if isinstance(ports, int):
        port_list.append(ports)
    elif isinstance(ports, str):
        port_list.extend(
            [int(p) for p in ports.split(',') if p.isdigit()]
        )
    elif isinstance(ports, list):
        port_list = ports
    port_list = list(map(int, filter(is_valid_port, port_list)))
    return port_list

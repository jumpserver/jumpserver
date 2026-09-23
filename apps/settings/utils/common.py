# coding: utf-8
from jumpserver.context_processor import default_interface
from django.conf import settings
from IPy import IP

from common.utils import lookup_domain


def get_interface_setting_or_default():
    if not settings.XPACK_ENABLED:
        return default_interface

    from xpack.plugins.interface.models import Interface
    return Interface.get_interface_setting(default_interface)


def get_login_title():
    return get_interface_setting_or_default()['login_title']


def generate_ips(address_string, max_count=None):
    def transform(_ip):
        real_ip, err_msg = lookup_domain(_ip)
        return _ip if err_msg or real_ip == '0.0.0.0' else real_ip

    # 支持的格式
    # 192.168.1.1,192.168.1.2
    # 192.168.1.1-12 | 192.168.1.1-192.168.1.12 | 192.168.1.0/30 | 192.168.1.1
    if max_count is not None and len(address_string) > max_count * 256:
        raise ValueError('Target specification is too long')
    ips = []
    ip_list = address_string.split(',')
    if max_count is not None and len(ip_list) > max_count:
        raise ValueError(f'At most {max_count} target addresses may be scanned')
    if len(ip_list) >= 1:
        count = 0
        for ip in ip_list:
            try:
                address = IP(transform(ip))
            except ValueError:
                continue
            count += address.len()
            if max_count is not None and count > max_count:
                raise ValueError(f'At most {max_count} target addresses may be scanned')
            ips.append(str(address))
        if ips:
            return ips

    ip_list = address_string.split('-')
    try:
        if len(ip_list) == 2:
            start_ip, end_ip = ip_list
            if ip_list[1].find('.') == -1:
                end_ip = start_ip[:start_ip.rindex('.') + 1] + end_ip
            start, end = IP(start_ip).int(), IP(end_ip).int()
            count = end - start + 1
            addresses = (str(addr) for value in range(start, end + 1) for addr in IP(value))
        else:
            network = IP(ip_list[0])
            count = network.len()
            addresses = (str(ip) for ip in network)
    except ValueError:
        return []
    if max_count is not None and count > max_count:
        raise ValueError(f'At most {max_count} target addresses may be scanned')
    ips.extend(addresses)
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

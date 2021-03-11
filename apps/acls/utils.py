from ipaddress import ip_network, ip_address


def is_ip_address(address):
    """ 192.168.10.1 """
    try:
        ip_address(address)
    except ValueError:
        return False
    else:
        return True


def is_ip_network(ip):
    """ 192.168.1.0/24 """
    try:
        ip_network(ip)
    except ValueError:
        return False
    else:
        return True


def is_ip_segment(ip):
    """ 10.1.1.1-10.1.1.20 """
    if '-' not in ip:
        return False
    ip_address1, ip_address2 = ip.split('-')
    return is_ip_address(ip_address1) and is_ip_address(ip_address2)


def in_ip_segment(ip, ip_segment):
    ip1, ip2 = ip_segment.split('-')
    ip1 = int(ip_address(ip1))
    ip2 = int(ip_address(ip2))
    ip = int(ip_address(ip))
    return min(ip1, ip2) <= ip <= max(ip1, ip2)


def contains_ip(ip, ip_group):
    """
    ip_group:
    [192.168.10.1, 192.168.1.0/24, 10.1.1.1-10.1.1.20, 2001:db8:2de::e13, 2001:db8:1a:1110::/64.]

    """

    if '*' in ip_group:
        return True

    for _ip in ip_group:
        if is_ip_address(_ip):
            # 192.168.10.1
            if ip == _ip:
                return True
        elif is_ip_network(_ip) and is_ip_address(ip):
            # 192.168.1.0/24
            if ip_address(ip) in ip_network(_ip):
                return True
        elif is_ip_segment(_ip) and is_ip_address(ip):
            # 10.1.1.1-10.1.1.20
            if in_ip_segment(ip, _ip):
                return True
        else:
            # is domain name
            if ip == _ip:
                return True

    return False

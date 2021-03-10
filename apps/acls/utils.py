from ipaddress import ip_network, ip_address


def is_ip_address(ip):
    """ 192.168.10.1 """
    try:
        ip_address(ip)
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
    ip_address1, ip_address2 = ip.split('-')
    return is_ip_address(ip_address1) and is_ip_address(ip_address2)


def contains_ip(ip, ip_group):
    """
    ip_group:
    ['192.168.10.1, 192.168.1.0/24, 10.1.1.1-10.1.1.20, 2001:db8:2de::e13, 2001:db8:1a:1110::/64.]

    """

    if '*' in ip_group:
        return True

    for _ip in ip_group:
        if is_ip_address(_ip):
            pass
        elif is_ip_network(_ip):
            pass
        elif is_ip_segment(_ip):
            pass
        else:
            # is domain name
            pass

    if '*' in ip_group:
        return True
    else:
        return ip in ip_group

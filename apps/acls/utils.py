from ipaddress import ip_network, ip_address


def is_valid_ip_address(ip):
    try:
        ip_address(ip)
    except ValueError:
        return False
    else:
        return True


def is_valid_ip_network(ip):
    try:
        ip_network(ip)
    except ValueError:
        return False
    else:
        return True


def contains_ip(ip, ip_group):
    """
    ip_group:
    ['192.168.10.1, 192.168.1.0/24, 10.1.1.1-10.1.1.20, 2001:db8:2de::e13, 2001:db8:1a:1110::/64.]

    """

    for _ip in ip_group:
        if is_valid_ip_address(_ip):
            pass
        elif is_valid_ip_network(_ip):
            pass
        else:
            pass

    if '*' in ip_group:
        return True
    else:
        return ip in ip_group

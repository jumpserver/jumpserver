from ipaddress import ip_network, ip_address, IPv4Address, AddressValueError, NetmaskValueError


def is_ip_address(address, only_ipv4=False):
    """ 192.168.10.1 """

    if only_ipv4:
        try:
            IPv4Address(address)
        except (AddressValueError, NetmaskValueError):
            return False
            pass
        else:
            return True
    else:
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


def is_ip_segment(ip, only_ipv4=False):
    """ 10.1.1.1-10.1.1.20 """
    ip_address1, ip_address2 = ip.split('-')
    return is_ip_address(ip_address1, only_ipv4) and is_ip_address(ip_address2, only_ipv4)


def contains_ip(ip, ip_group):
    """
    ip_group:
    ['192.168.10.1, 192.168.1.0/24, 10.1.1.1-10.1.1.20, 2001:db8:2de::e13, 2001:db8:1a:1110::/64.]

    """

    if '*' in ip_group:
        return True

    for _ip in ip_group:
        if is_ip_address(_ip):
            if ip == _ip:
                return True
        elif is_ip_network(_ip) and is_ip_address(ip):
            if ip_address(ip) in ip_network(_ip):
                return True
        elif is_ip_segment(_ip, only_ipv4=True):
            ip_1, ip_2 = _ip.split('-')
            ip_bits = ip.split('.')
            ip_1_bits = ip_1.split('.')
            ip_2_bits = ip_2.split('.')
            ip_bits_range = zip(ip_bits, ip_1_bits, ip_2_bits)
            for ip_bit_range in ip_bits_range:
                bit_range = range(min(ip_bit_range[1:]), max(ip_bit_range[1:])+1)
                if ip_bit_range[0] not in bit_range:
                    break
        else:
            # is domain name
            if ip == _ip:
                return True
    return False

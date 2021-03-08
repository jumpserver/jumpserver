
def contains_ip(ip, ip_group):
    if '*' in ip_group:
        return True
    else:
        return ip in ip_group

import time
import nmap

from IPy import IP

from common.utils.timezone import local_now_display


def generate_ips(ip_string):
    # 支持的格式
    # 192.168.1.1-12 | 192.168.1.1-192.168.1.12 | 192.168.1.0/30 | 192.168.1.1
    ip_list = ip_string.split('-')
    ips = []
    try:
        if len(ip_list) == 2:
            start_ip, end_ip = ip_list
            if ip_list[1].find('.') == -1:
                end_ip = start_ip[:start_ip.rindex('.') + 1] + end_ip
            for ip in range(IP(start_ip).int(), IP(end_ip).int() + 1):
                ips.extend(IP(ip))
        else:
            ips.extend(IP(ip_list[0]))
    except Exception:
        ips = []
    return ips


def once_nmap(nm, ip, ports, timeout, display):
    nmap_version = '.'.join(map(lambda x: str(x), nm.nmap_version()))
    display(f'Starting Nmap {nmap_version} at {local_now_display()} for {ip}')
    try:
        is_ok = True
        nm.scan(ip, arguments='-sS -sU -F', ports=ports, timeout=timeout)
        tcp_port = nm[ip].get('tcp', {})
        udp_port = nm[ip].get('udp', {})
        display(f'PORT\tSTATE\tSERVICE')
        for port, info in tcp_port.items():
            display(f"{port}\t{info.get('state', 'unknown')}\t{info.get('name', 'unknown')}")
        for port, info in udp_port.items():
            display(f"{port}\t{info.get('state', 'unknown')}\t{info.get('name', 'unknown')}")
    except Exception:
        is_ok = False
        display(f'Nmap scan report for {ip} error.')
    return is_ok


def verbose_nmap(dest_ip, dest_port=None, timeout=None, display=print):
    dest_port = ','.join(list(dest_port)) if dest_port else None

    ips = generate_ips(dest_ip)
    nm = nmap.PortScanner()
    success_num, start_time = 0, time.time()
    display(f'[Summary] Nmap: {len(ips)} IP addresses were scanned')
    for ip in ips:
        ok = once_nmap(nm, str(ip), dest_port, timeout, display)
        if ok:
            success_num += 1
        display('')
    display(f'[Done] Nmap: {len(ips)} IP addresses ({success_num} hosts up) '
            f'scanned in {round(time.time() - start_time, 2)} seconds')

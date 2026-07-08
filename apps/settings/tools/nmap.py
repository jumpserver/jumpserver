import argparse
import asyncio
import socket
import time

from common.utils.timezone import local_now_display
from settings.utils import generate_ips

_SCANNER_VERSION = '1.0'

# Fallback service name table for platforms where getservbyport is unavailable
_KNOWN_SERVICES = {
    21: 'ftp', 22: 'ssh', 23: 'telnet', 25: 'smtp', 53: 'domain',
    80: 'http', 110: 'pop3', 135: 'msrpc', 139: 'netbios-ssn',
    143: 'imap', 443: 'https', 445: 'microsoft-ds', 587: 'submission',
    993: 'imaps', 995: 'pop3s', 1433: 'ms-sql-s', 1521: 'oracle',
    3306: 'mysql', 3389: 'ms-wbt-server', 5432: 'postgresql',
    5900: 'vnc', 6379: 'redis', 8080: 'http-proxy', 8443: 'https-alt',
    27017: 'mongodb',
}


def _parse_ports(ports_str):
    """Parse '22,80,443' or '22-100' or a mix into a sorted list of ints."""
    if not ports_str:
        # mirror nmap's default: the 1000 most common ports; use 1-1024 as a
        # reasonable approximation without requiring root privileges.
        return list(range(1, 1025))
    ports = []
    for part in ports_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            ports.extend(range(int(start), int(end) + 1))
        else:
            ports.append(int(part))
    return sorted(set(ports))


def _service_name(port: int, proto: str = 'tcp') -> str:
    try:
        return socket.getservbyport(port, proto)
    except OSError:
        return _KNOWN_SERVICES.get(port, 'unknown')


async def _scan_tcp_port(ip: str, port: int, timeout: float) -> str:
    """Return 'open' or 'closed' for a single TCP port."""
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port), timeout=timeout
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return 'open'
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return 'closed'


async def get_nmap_result(ip: str, ports_str, timeout) -> list[str]:
    """Scan *ip* and return formatted result lines (PORT / STATE / SERVICE)."""
    timeout = float(timeout) if timeout else 1.0
    ports = _parse_ports(ports_str)

    states = await asyncio.gather(
        *[_scan_tcp_port(ip, p, timeout) for p in ports]
    )

    lines = ['PORT\tSTATE\tSERVICE']
    for port, state in zip(ports, states):
        if state == 'open':
            lines.append(f'{port}/tcp\t{state}\t{_service_name(port)}')
    return lines


async def once_nmap(ip: str, ports_str, timeout, display) -> bool:
    await display(f'Starting Nmap at {local_now_display()} for {ip}')
    try:
        results = await get_nmap_result(ip, ports_str, timeout)
        for line in results:
            await display(line)
        is_ok = len(results) > 1  # at least one open port found
    except Exception as err:
        is_ok = False
        await display(f'Error: {err}')
    return is_ok


async def verbose_nmap(dest_ips, dest_ports=None, timeout=None, display=None):
    if not display:
        return

    ips = generate_ips(dest_ips)
    dest_port = ','.join(list(dest_ports)) if dest_ports else None

    success_num, start_time = 0, time.time()
    await display(f'[Summary] Nmap (v{_SCANNER_VERSION}): {len(ips)} addresses were scanned')
    for ip in ips:
        ok = await once_nmap(str(ip), dest_port, timeout, display)
        if ok:
            success_num += 1
        await display()
    await display(
        f'[Done] Nmap: {len(ips)} IP addresses ({success_num} hosts up) '
        f'scanned in {round(time.time() - start_time, 2)} seconds'
    )


async def _main():
    parser = argparse.ArgumentParser(description='Pure-Python TCP port scanner')
    parser.add_argument('targets', nargs='+', help='IP / CIDR, e.g. 192.168.1.1 or 10.0.0.0/24')
    parser.add_argument('-p', '--ports', default=None,
                        help='Ports to scan, e.g. 22,80,443 or 22-1024 (default: 1-1024)')
    parser.add_argument('--timeout', type=float, default=1.0,
                        help='Per-port connect timeout in seconds (default: 1.0)')
    args = parser.parse_args()

    async def display(msg=''):
        print(msg)

    dest_ports = args.ports.split(',') if args.ports else None
    await verbose_nmap(args.targets, dest_ports=dest_ports, timeout=args.timeout, display=display)


if __name__ == '__main__':
    asyncio.run(_main())

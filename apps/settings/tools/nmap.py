import argparse
import asyncio
import errno
import socket
import threading
import time

from common.utils.timezone import local_now_display
from settings.utils import generate_ips

_SCANNER_VERSION = '1.0'
_MAX_HOSTS = 256
_MAX_PORTS = 4096
_MAX_PROBES = 65536
_PORT_CONCURRENCY = 32
_MAX_CONNECT_TIMEOUT = 10
_SCAN_TIMEOUT = 120
# Shared by requests in this process; do not queue excess scans.
_SCAN_SLOTS = threading.BoundedSemaphore(2)

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
    if not isinstance(ports_str, str) or len(ports_str) > _MAX_PORTS * 12:
        raise ValueError('Invalid port specification')
    parts = ports_str.split(',')
    if len(parts) > _MAX_PORTS:
        raise ValueError(f'At most {_MAX_PORTS} ports may be scanned')

    ranges = []
    for part in parts:
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-', 1))
        else:
            start = end = int(part)
        if not 1 <= start <= end <= 65535:
            raise ValueError('Ports must be between 1 and 65535 in ascending order')
        ranges.append((start, end))

    ports, last_end = [], 0
    for start, end in sorted(ranges):
        start = max(start, last_end + 1)
        if start > end:
            continue
        if len(ports) + end - start + 1 > _MAX_PORTS:
            raise ValueError(f'At most {_MAX_PORTS} ports may be scanned')
        ports.extend(range(start, end + 1))
        last_end = end
    return ports


def _parse_timeout(timeout):
    timeout = float(timeout) if timeout else 1.0
    if not 0 < timeout <= _MAX_CONNECT_TIMEOUT:
        raise ValueError(
            f'Connection timeout must be greater than 0 and at most {_MAX_CONNECT_TIMEOUT} seconds'
        )
    return timeout


def _service_name(port: int, proto: str = 'tcp') -> str:
    try:
        return socket.getservbyport(port, proto)
    except OSError:
        return _KNOWN_SERVICES.get(port, 'unknown')


async def _scan_tcp_port(ip: str, port: int, timeout: float) -> tuple[str, bool]:
    """Return the port state and whether the response proves the host is up."""
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port), timeout=timeout
        )
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=1)
        except asyncio.CancelledError:
            writer.transport.abort()
            raise
        except Exception:
            writer.transport.abort()
        return 'open', True
    except ConnectionRefusedError:
        return 'closed', True
    except asyncio.TimeoutError:
        return 'filtered', False
    except OSError as err:
        if err.errno == errno.ECONNREFUSED:
            return 'closed', True
        if err.errno == errno.ETIMEDOUT:
            return 'filtered', False
        return 'unreachable', False


async def get_nmap_result(ip: str, ports_str, timeout) -> tuple[list[str], bool]:
    """Scan *ip* and return formatted result lines plus host reachability."""
    timeout = _parse_timeout(timeout)
    ports = _parse_ports(ports_str)

    states = []
    for offset in range(0, len(ports), _PORT_CONCURRENCY):
        async with asyncio.TaskGroup() as group:
            tasks = [
                group.create_task(_scan_tcp_port(ip, port, timeout))
                for port in ports[offset:offset + _PORT_CONCURRENCY]
            ]
        states.extend(task.result() for task in tasks)

    lines = ['PORT\tSTATE\tSERVICE']
    for port, (state, _) in zip(ports, states):
        lines.append(f'{port}/tcp\t{state}\t{_service_name(port)}')
    is_host_up = any(is_reachable for _, is_reachable in states)
    return lines, is_host_up


async def once_nmap(ip: str, ports_str, timeout, display) -> bool:
    await display(f'Starting Nmap at {local_now_display()} for {ip}')
    try:
        results, is_ok = await get_nmap_result(ip, ports_str, timeout)
        for line in results:
            await display(line)
    except Exception as err:
        is_ok = False
        await display(f'Error: {err}')
    return is_ok


async def verbose_nmap(dest_ips, dest_ports=None, timeout=None, display=None):
    if not display:
        return

    if not _SCAN_SLOTS.acquire(blocking=False):
        await display('Error: Too many active scans; please try again later')
        return

    try:
        if dest_ports and (len(dest_ports) > _MAX_PORTS or any(len(p) > 32 for p in dest_ports)):
            raise ValueError('Port specification is too large')
        dest_port = ','.join(list(dest_ports)) if dest_ports else None
        ports = _parse_ports(dest_port)
        timeout = _parse_timeout(timeout)
        ips = generate_ips(dest_ips, max_count=_MAX_HOSTS)
        if len(ips) * len(ports) > _MAX_PROBES:
            raise ValueError(f'At most {_MAX_PROBES} address/port pairs may be scanned')

        success_num, start_time = 0, time.monotonic()
        async with asyncio.timeout(_SCAN_TIMEOUT):
            await display(f'[Summary] Nmap (v{_SCANNER_VERSION}): {len(ips)} addresses were scanned')
            for ip in ips:
                ok = await once_nmap(str(ip), dest_port, timeout, display)
                if ok:
                    success_num += 1
                await display()
            await display(
                f'[Done] Nmap: {len(ips)} IP addresses ({success_num} hosts up) '
                f'scanned in {round(time.monotonic() - start_time, 2)} seconds'
            )
    except asyncio.TimeoutError:
        await display(f'Error: Scan exceeded {_SCAN_TIMEOUT} seconds')
    except (TypeError, ValueError) as err:
        await display(f'Error: {err}')
    finally:
        _SCAN_SLOTS.release()


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

import asyncio
import time
import nmap

from common.utils.timezone import local_now_display
from settings.utils import generate_ips


def get_nmap_result(nm, ip, ports, timeout):
    results = []
    nm.scan(ip, ports=ports, timeout=timeout)
    tcp_port = nm[ip].get('tcp', {})
    udp_port = nm[ip].get('udp', {})
    results.append(f'PORT\tSTATE\tSERVICE')
    for port, info in tcp_port.items():
        results.append(f"{port}\t{info.get('state', 'unknown')}\t{info.get('name', 'unknown')}")
    for port, info in udp_port.items():
        results.append(f"{port}\t{info.get('state', 'unknown')}\t{info.get('name', 'unknown')}")
    return results


async def once_nmap(nm, ip, ports, timeout, display):
    await display(f'Starting Nmap at {local_now_display()} for {ip}')
    try:
        is_ok = True
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, get_nmap_result, nm, ip, ports, timeout)
        for result in results:
            await display(result)

    except KeyError:
        is_ok = False
        await display(f'Host seems down.')
    except Exception as err:
        is_ok = False
        await display(f"Error: %s" % err)
    return is_ok


async def verbose_nmap(dest_ips, dest_ports=None, timeout=None, display=None):
    if not display:
        return

    ips = generate_ips(dest_ips)
    dest_port = ','.join(list(dest_ports)) if dest_ports else None

    nm = nmap.PortScanner()
    success_num, start_time = 0, time.time()
    nmap_version = '.'.join(map(lambda x: str(x), nm.nmap_version()))
    await display(f'[Summary] Nmap (v{nmap_version}): {len(ips)} addresses were scanned')
    for ip in ips:
        ok = await once_nmap(nm, str(ip), dest_port, timeout, display)
        if ok:
            success_num += 1
        await display()
    await display(f'[Done] Nmap: {len(ips)} IP addresses ({success_num} hosts up) '
                  f'scanned in {round(time.time() - start_time, 2)} seconds')

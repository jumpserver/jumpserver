import asyncio
import netifaces
import socket
import struct

from common.utils.timezone import local_now_display
from settings.utils import generate_ips, generate_ports


async def once_tcpdump(
        interface, src_ips, src_ports, dest_ips, dest_ports, display, stop_event
):
    loop = asyncio.get_event_loop()
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
    s.bind((interface, 0))
    s.setblocking(False)
    while not stop_event.is_set():
        try:
            packet = await loop.sock_recv(s, 65535)
        except BlockingIOError:
            await asyncio.sleep(0.1)
        # 解析IP数据包
        ip_header = packet[14:34]
        ip_hdr = struct.unpack('!BBHHHBBH4s4s', ip_header)
        # 判断是否为TCP数据包
        protocol = ip_hdr[6]
        if protocol != 6:
            continue
        # 解析TCP数据包
        tcp_header = packet[34:54]
        tcp_hdr = struct.unpack('!HHLLBBHHH', tcp_header)
        # 获取源地址、源端口号、目标地址、目标端口等信息
        src_ip, dest_ip = map(lambda x: socket.inet_ntoa(x), ip_hdr[8:10])
        src_port, dest_port = tcp_hdr[0], tcp_hdr[1]
        # 获取数据包类型和长度
        packet_type = socket.htons(ip_hdr[6])
        packet_len = len(packet)
        # 获取TCP标志位、序号、确认号、部分数据等信息
        seq, ack, flags = tcp_hdr[2], tcp_hdr[3], tcp_hdr[5]
        data = packet[54:]
        # 如果过滤的参数[源地址、源端口等]为空，则不过滤
        # 各个过滤参数之间为 `且` 的关系
        green_light = True
        if src_ips and src_ip not in src_ips:
            green_light = False
        if src_ports and src_port not in src_ports:
            green_light = False
        if dest_ips and dest_ip not in dest_ips:
            green_light = False
        if dest_ports and dest_port not in dest_ports:
            green_light = False
        if not green_light:
            continue

        results = [
            f'[{interface}][{local_now_display()}] {src_ip}:{src_port} -> '
            f'{dest_ip}:{dest_port} ({packet_type}, {packet_len} bytes)',
            f'\tFlags: {flags} Seq: {seq}, Ack: {ack}', f'\tData: {data}'
        ]
        for r in results:
            await display(r)


def list_show(items, default='all'):
    return ','.join(map(str, items)) or default


async def verbose_tcpdump(interfaces, src_ips, src_ports, dest_ips, dest_ports, display=None):
    if not display:
        return

    stop_event = asyncio.Event()
    valid_interface = netifaces.interfaces()
    if interfaces:
        valid_interface = set(netifaces.interfaces()) & set(interfaces)

    src_ips = generate_ips(src_ips)
    src_ports = generate_ports(src_ports)
    dest_ips = generate_ips(dest_ips)
    dest_ports = generate_ports(dest_ports)

    summary = [
        f"[Summary] Tcpdump filter info: ",
        f"Interface: [{list_show(valid_interface)}]",
        f"Source address: [{list_show(src_ips)}]",
        f"source port: [{list_show(src_ports)}]",
        f"Destination address: [{list_show(dest_ips)}]",
        f"Destination port: [{list_show(dest_ports)}]",
    ]
    for s in summary:
        await display(s)

    params = [src_ips, src_ports, dest_ips, dest_ports, display, stop_event]
    tasks = [
        asyncio.create_task(once_tcpdump(i, *params)) for i in valid_interface
    ]
    await asyncio.gather(*tasks)
    stop_event.set()

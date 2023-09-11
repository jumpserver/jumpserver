# -*- coding: utf-8 -*-
#
import asyncio
import socket
import struct
import time

from settings.utils import generate_ips


def calculate_checksum(data):
    # 计算 ICMP 校验和
    checksum = 0
    if len(data) % 2 == 1:
        data += b'\x00'
    for i in range(0, len(data), 2):
        w = (data[i] << 8) + data[i+1]
        checksum += w
    checksum = (checksum >> 16) + (checksum & 0xffff)
    checksum = ~checksum & 0xffff
    return checksum


async def once_traceroute(target, display, max_hops=30, timeout=3):
    loop = asyncio.get_event_loop()
    icmp = socket.getprotobyname('icmp')
    sock_fd = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
    for ttl in range(1, max_hops+1):
        # 设置 TTL
        sock_fd.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
        # 设置超时时间
        sock_fd.settimeout(timeout)
        # 发送 ICMP Echo 请求数据包
        packet = struct.pack('!BBHHH', 8, 0, 0, 12345, ttl)
        checksum = calculate_checksum(packet)
        packet = struct.pack('!BBHHH', 8, 0, checksum, 12345, ttl)
        start_time = time.time()
        sock_fd.sendto(packet, (target, 0))
        await asyncio.sleep(0.01)
        try:
            # 接收 ICMP Echo Reply 数据包
            recv_packet, addr = await loop.sock_recvfrom(sock_fd, 1024)
            end_time = time.time()
            # 解析目标地址
            dest_ip = addr[0]
            # 获取跃点信息
            hop_info = f'{ttl} {dest_ip} ({dest_ip})'
            # 获取延迟时间信息
            delay_info = f'{(end_time - start_time) * 1000:.3f} ms'
            # 打印跃点信息和延迟时间
            await display(f'{hop_info:<4} {delay_info}')
            if dest_ip == target:
                return
        except socket.timeout:
            # 发生超时，跳出循环
            await display(f'{ttl} *')
    sock_fd.close()


async def verbose_traceroute(dest_ips, timeout=10, display=None):
    if not display:
        return

    ips = generate_ips(dest_ips)
    await display(f'Total valid address: {len(ips)}\r\n')
    for dest_ip in ips:
        await display(f'traceroute to {dest_ip}, 30 hops max, 60 byte packets')
        msg = ''
        try:
            await once_traceroute(dest_ip, display)
        except Exception as e:
            msg = f'Error: {e}'
        await display(msg)

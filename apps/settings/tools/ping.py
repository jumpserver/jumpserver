# -*- coding: utf-8 -*-
#
import asyncio
import os
import select
import socket
import struct
import time

from common.utils import lookup_domain
from settings.utils import generate_ips

# From /usr/include/linux/icmp.h; your milage may vary.
ICMP_ECHO_REQUEST = 8  # Seems to be the same on Solaris.
ICMPV6_ECHO_REQUEST = 128
ICMPV6_ECHO_REPLY = 129


def checksum(source_string):
    """
    I'm not too confident that this is right but testing seems
    to suggest that it gives the same answers as in_cksum in ping.c
    """
    sum = 0
    count_to = int((len(source_string) / 2) * 2)
    for count in range(0, count_to, 2):
        this = source_string[count + 1] * 256 + source_string[count]
        sum = sum + this
        sum &= 0xffffffff  # Necessary?

    if count_to < len(source_string):
        sum += ord(source_string[len(source_string) - 1])
        sum &= 0xffffffff  # Necessary?

    sum = (sum >> 16) + (sum & 0xffff)
    sum += sum >> 16
    answer = ~sum
    answer &= 0xffff

    # Swap bytes. Bugger me if I know why.
    answer = answer >> 8 | (answer << 8 & 0xff00)

    return answer


def _get_icmp_header_offset(received_packet, family):
    if family != socket.AF_INET6:
        return 20
    if received_packet and (received_packet[0] >> 4) == 6:
        return 40
    return 0


def receive_one_ping(my_socket, id, timeout, family):
    """
    Receive the ping from the socket.
    """
    time_left = timeout
    while True:
        started_select = time.time()
        what_ready = select.select([my_socket], [], [], time_left)
        how_long_in_select = time.time() - started_select
        if not what_ready[0]:  # Timeout
            return

        time_received = time.time()
        received_packet, addr = my_socket.recvfrom(1024)
        header_offset = _get_icmp_header_offset(received_packet, family)
        icmpHeader = received_packet[header_offset:header_offset + 8]
        if len(icmpHeader) < 8:
            continue
        type, code, checksum, packet_id, sequence = struct.unpack("BBHHH", icmpHeader)
        if family == socket.AF_INET6 and type != ICMPV6_ECHO_REPLY:
            continue
        if packet_id == id:
            bytes = struct.calcsize("d")
            if len(received_packet) < header_offset + 8 + bytes:
                continue
            time_sent = struct.unpack(
                "d", received_packet[header_offset + 8: header_offset + 8 + bytes]
            )[0]
            return time_received - time_sent

        time_left -= how_long_in_select
        if time_left <= 0:
            return


def send_one_ping(my_socket, dest_addr, id, psize, family):
    """
    Send one ping to the given >dest_addr<.
    """
    if family == socket.AF_INET6:
        dest_addr = dest_addr
        icmp_type = ICMPV6_ECHO_REQUEST
    else:
        if isinstance(dest_addr, tuple):
            dest_addr = (dest_addr[0], 1)
        else:
            dest_addr = (socket.gethostbyname(dest_addr), 1)
        icmp_type = ICMP_ECHO_REQUEST

    # Remove header size from packet size
    # psize = psize - 8
    # laixintao edit:
    # Do not need to remove header here. From BSD ping man:
    #     The default is 56, which translates into 64 ICMP data
    #     bytes when combined with the 8 bytes of ICMP header data.

    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    my_checksum = 0

    # Make a dummy heder with a 0 checksum.
    header = struct.pack("BBHHH", icmp_type, 0, my_checksum, id, 1)
    bytes = struct.calcsize("d")
    data = (psize - bytes) * b"Q"
    data = struct.pack("d", time.time()) + data

    if family != socket.AF_INET6:
        # Calculate the checksum on the data and the dummy header.
        my_checksum = checksum(header + data)

    # Now that we have the right checksum, we put that in. It's just easier
    # to make up a new header than to stuff it into the dummy.
    header = struct.pack(
        "BBHHH", icmp_type, 0, socket.htons(my_checksum), id, 1
    )
    packet = header + data
    my_socket.sendto(packet, dest_addr)


def resolve_dest_addr(dest_addr):
    addrinfos = socket.getaddrinfo(
        dest_addr, None, socket.AF_UNSPEC, socket.SOCK_DGRAM
    )
    family, _, _, _, sockaddr = addrinfos[0]
    return family, sockaddr


def ping(dest_addr, timeout, psize, flag=0):
    """
    Returns either the delay (in seconds) or none on timeout.
    """
    family, dest_sockaddr = resolve_dest_addr(dest_addr)
    if family == socket.AF_INET6:
        icmp = socket.IPPROTO_ICMPV6
        sock_type = socket.SOCK_DGRAM
    else:
        icmp = socket.getprotobyname("icmp")
        sock_type = socket.SOCK_DGRAM if os.getuid() != 0 else socket.SOCK_RAW
    try:
        my_socket = socket.socket(family, sock_type, icmp)
    except socket.error as e:
        if e.errno == 1:
            # Operation not permitted
            msg = str(e)
            raise socket.error(msg)
        raise  # raise the original error

    process_pre = os.getpid() & 0xFF00
    flag &= 0x00FF
    my_id = process_pre | flag

    send_one_ping(my_socket, dest_sockaddr, my_id, psize, family)
    delay = receive_one_ping(my_socket, my_id, timeout, family)

    my_socket.close()
    return delay


async def verbose_ping(dest_ips, timeout=2, count=5, psize=64, display=None):
    """
    Send `count' ping with `psize' size to `dest_addr' with
    the given `timeout' and display the result.
    """
    if not display:
        return

    result = {}
    ips = generate_ips(dest_ips)
    await display(f'Total valid address: {len(ips)}\r\n')
    for dest_ip in ips:
        await display(f'PING {dest_ip}: 56 data bytes')
        # 切换异步协程
        await asyncio.sleep(0.01)
        error_count = 0
        for i in range(count):
            try:
                delay = ping(dest_ip, timeout, psize)
            except socket.gaierror as e:
                await display("Failed (socket error: '%s')" % str(e))
                error_count += 1
                break

            if delay is None:
                await display("Request timeout for icmp_seq %i" % i)
                error_count += 1
            else:
                delay *= 1000
                await display("64 bytes from %s: time=%.3f ms" % (dest_ip, delay))
            await asyncio.sleep(1)
        # 只要有包通过，就认为address是通的
        result[dest_ip] = 'failed' if error_count == count else 'ok'
        await display(f'{count} packets transmitted, '
                      f'{count - error_count} packets received, '
                      f'{(error_count / count) * 100}% packet loss\r\n')

    await display(f'----- Ping statistics -----')
    for k, v in result.items():
        await display(f'{k}: {v}')


if __name__ == "__main__":
    verbose_ping("google.com")
    verbose_ping("192.168.4.1")
    verbose_ping("www.baidu.com")
    verbose_ping("sssssss")

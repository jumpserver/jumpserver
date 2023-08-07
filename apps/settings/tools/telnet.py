# -*- coding: utf-8 -*-
#
import asyncio

from common.utils import lookup_domain

PROMPT_REGEX = r'[\<|\[](.*)[\>|\]]'


async def telnet(dest_addr, port_number=23, timeout=10):
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(dest_addr, port_number), timeout
        )
    except asyncio.TimeoutError:
        return False, 'Timeout'
    except (ConnectionRefusedError, OSError) as e:
        return False, str(e)
    try:
        # 发送命令
        writer.write(b"command\r\n")
        await writer.drain()
        # 读取响应
        response = await reader.readuntil()
    except asyncio.TimeoutError:
        writer.close()
        await writer.wait_closed()
        return False, 'Timeout'
    writer.close()
    await writer.wait_closed()
    return True, response.decode('utf-8', 'ignore')


async def verbose_telnet(dest_ip, dest_port=23, timeout=10, display=None):
    if not display:
        return

    ip, err = lookup_domain(dest_ip)
    if not ip:
        await display(err)
        return

    await display(f'Trying {dest_ip} ({ip}:{dest_port})')
    try:
        is_connective, resp = await telnet(dest_ip, dest_port, timeout)
        if is_connective:
            msg = f'Connected to {dest_ip} {dest_port} {resp}.\r\n' \
                  f'Connection closed by foreign host.'
        else:
            msg = f'Unable to connect to remote host\r\n' \
                  f'Reason: {resp}'
    except Exception as e:
        msg = 'Error: %s' % e
    await display(msg)


if __name__ == "__main__":
    print(verbose_telnet(dest_addr='1.1.1.1', port_number=2222))
    print(verbose_telnet(dest_addr='baidu.com', port_number=80))
    print(verbose_telnet(dest_addr='baidu.com', port_number=8080))
    print(verbose_telnet(dest_addr='192.168.4.1', port_number=2222))
    print(verbose_telnet(dest_addr='192.168.4.1', port_number=2223))
    print(verbose_telnet(dest_addr='ssssss', port_number=-1))

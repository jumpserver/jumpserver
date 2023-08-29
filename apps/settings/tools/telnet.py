# -*- coding: utf-8 -*-
#
import asyncio
import socket
import telnetlib

from settings.utils import generate_ips

PROMPT_REGEX = r'[\<|\[](.*)[\>|\]]'


async def telnet(dest_addr, port_number=23, timeout=10):
    loop = asyncio.get_running_loop()
    try:
        connection = await loop.run_in_executor(None, telnetlib.Telnet, dest_addr, port_number, timeout)
    except asyncio.TimeoutError:
        return False, 'Timeout'
    except (ConnectionRefusedError, socket.timeout, socket.gaierror) as e:
        return False, str(e)
    expected_regexes = [bytes(PROMPT_REGEX, encoding='ascii')]
    __, __, output = connection.expect(expected_regexes, timeout=3)
    return True, output.decode('utf-8', 'ignore')


async def verbose_telnet(dest_ips, dest_port=23, timeout=10, display=None):
    if not display:
        return

    result = {}
    ips = generate_ips(dest_ips)
    await display(f'Total valid address: {len(ips)}\r\n')
    for dest_ip in ips:
        await display(f'Trying ({dest_ip}:{dest_port})')
        try:
            is_connective, resp = await telnet(dest_ip, dest_port, timeout)
            if is_connective:
                result[dest_ip] = 'ok'
                msg = f'Connected to {dest_ip} {dest_port} {resp}.\r\n' \
                      f'Connection closed by foreign host.'
            else:
                result[dest_ip] = 'failed'
                msg = f'Unable to connect to remote host\r\n' \
                      f'Reason: {resp}'
        except Exception as e:
            msg = 'Error: %s' % e
        await display(f'{msg}\r\n')

    await display(f'----- Telnet statistics -----')
    for k, v in result.items():
        await display(f'{k}: {v}')


if __name__ == "__main__":
    print(verbose_telnet(dest_addr='1.1.1.1', port_number=2222))
    print(verbose_telnet(dest_addr='baidu.com', port_number=80))
    print(verbose_telnet(dest_addr='baidu.com', port_number=8080))
    print(verbose_telnet(dest_addr='192.168.4.1', port_number=2222))
    print(verbose_telnet(dest_addr='192.168.4.1', port_number=2223))
    print(verbose_telnet(dest_addr='ssssss', port_number=-1))

# -*- coding: utf-8 -*-
#
import socket
import telnetlib

from common.utils import lookup_domain

PROMPT_REGEX = r'[\<|\[](.*)[\>|\]]'


def telnet(dest_addr, port_number=23, timeout=10):
    try:
        connection = telnetlib.Telnet(dest_addr, port_number, timeout)
    except (ConnectionRefusedError, socket.timeout, socket.gaierror) as e:
        return False, str(e)
    expected_regexes = [bytes(PROMPT_REGEX, encoding='ascii')]
    index, prompt_regex, output = connection.expect(expected_regexes, timeout=3)
    return True, output.decode('utf-8', 'ignore')


def verbose_telnet(dest_addr, port_number=23, timeout=10, display=None):
    if display is None:
        display = print
    ip = lookup_domain(dest_addr)
    if not ip:
        return
    msg = 'Trying %s (%s:%s)' % (dest_addr, ip, port_number)
    display(msg)
    try:
        is_connective, resp = telnet(dest_addr, port_number, timeout)
        if is_connective:
            template = 'Connected to {0} {1}.\r\n{2}Connection closed by foreign host.'
        else:
            template = 'telnet: connect to {0} {1} {2}\r\ntelnet: Unable to connect to remote host'
        msg = template.format(dest_addr, port_number, resp)
    except Exception as e:
        msg = 'Error: %s' % e
    display(msg)


if __name__ == "__main__":
    print(verbose_telnet(dest_addr='1.1.1.1', port_number=2222))
    print(verbose_telnet(dest_addr='baidu.com', port_number=80))
    print(verbose_telnet(dest_addr='baidu.com', port_number=8080))
    print(verbose_telnet(dest_addr='192.168.4.1', port_number=2222))
    print(verbose_telnet(dest_addr='192.168.4.1', port_number=2223))
    print(verbose_telnet(dest_addr='ssssss', port_number=-1))

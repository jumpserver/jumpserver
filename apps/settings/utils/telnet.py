# -*- coding: utf-8 -*-
#
import socket
import telnetlib

PROMPT_REGEX = r'[\<|\[](.*)[\>|\]]'


def telnet(dest_addr, port_number=23, timeout=10):
    try:
        connection = telnetlib.Telnet(dest_addr, port_number, timeout)
    except (ConnectionRefusedError, socket.timeout, socket.gaierror) as e:
        return False, str(e)
    expected_regexes = [bytes(PROMPT_REGEX, encoding='ascii')]
    index, prompt_regex, output = connection.expect(expected_regexes, timeout=3)
    return True, output.decode('utf-8', 'ignore')


if __name__ == "__main__":
    print(telnet(dest_addr='1.1.1.1', port_number=2222))
    print(telnet(dest_addr='baidu.com', port_number=80))
    print(telnet(dest_addr='baidu.com', port_number=8080))
    print(telnet(dest_addr='192.168.4.1', port_number=2222))
    print(telnet(dest_addr='192.168.4.1', port_number=2223))
    print(telnet(dest_addr='ssssss', port_number=-1))

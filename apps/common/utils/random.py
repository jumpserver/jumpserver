# -*- coding: utf-8 -*-
#
import struct
import random
import socket
import string


string_punctuation = '!#$%&()*+,-.:;<=>?@[]^_~'


def random_datetime(date_start, date_end):
    random_delta = (date_end - date_start) * random.random()
    return date_start + random_delta


def random_ip():
    return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))


def random_string(length, lower=True, upper=True, digit=True, special_char=False):
    chars = string.ascii_letters
    if digit:
        chars += string.digits

    while True:
        password = list(random.choice(chars) for i in range(length))
        if upper and not any(c.upper() for c in password):
            continue
        if lower and not any(c.lower() for c in password):
            continue
        if digit and not any(c.isdigit() for c in password):
            continue
        break

    if special_char:
        spc = random.choice(string_punctuation)
        i = random.choice(range(1, len(password)))
        password[i] = spc

    password = ''.join(password)
    return password

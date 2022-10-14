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
    chars, no_punctuation_chars = '', ''
    if lower:
        chars += string.ascii_lowercase
    if upper:
        chars += string.ascii_uppercase
    if digit:
        chars += string.digits

    no_punctuation_chars = chars
    if special_char:
        chars += string_punctuation

    random_str = ''.join(random.sample(chars, length - 1))
    random_prefix = random.choice(no_punctuation_chars)
    return random_prefix + random_str

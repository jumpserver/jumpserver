# -*- coding: utf-8 -*-
#
import random
import secrets
import socket
import string
import struct

string_punctuation = '!#$%&()*+,-.:;<=>?@[]^_~'


def random_datetime(date_start, date_end):
    random_delta = (date_end - date_start) * random.random()
    return date_start + random_delta


def random_ip():
    return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))


def random_string(length: int, lower=True, upper=True, digit=True, special_char=False, symbols=string_punctuation):
    if not any([lower, upper, digit]):
        raise ValueError('At least one of `lower`, `upper`, `digit` must be `True`')
    if length < 4:
        raise ValueError('The length of the string must be greater than 3')

    chars_map = (
        (lower, string.ascii_lowercase),
        (upper, string.ascii_uppercase),
        (digit, string.digits),
    )
    chars = ''.join([i[1] for i in chars_map if i[0]])
    texts = list(secrets.choice(chars) for __ in range(length))

    if special_char:
        symbol_num = length // 16 + 1
        symbol_index = random.choices(list(range(1, length - 1)), k=symbol_num)
        for i in symbol_index:
            texts[i] = secrets.choice(symbols)

    text = ''.join(texts)
    return text

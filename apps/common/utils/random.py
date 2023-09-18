# -*- coding: utf-8 -*-
#
import random
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
    args_names = ['lower', 'upper', 'digit']
    args_values = [lower, upper, digit]
    args_string = [string.ascii_lowercase, string.ascii_uppercase, string.digits]
    args_string_map = dict(zip(args_names, args_string))
    kwargs = dict(zip(args_names, args_values))
    kwargs_keys = list(kwargs.keys())
    kwargs_values = list(kwargs.values())
    args_true_count = len([i for i in kwargs_values if i])

    assert any(kwargs_values), f'Parameters {kwargs_keys} must have at least one `True`'
    assert length >= args_true_count, f'Expected length >= {args_true_count}, bug got {length}'

    chars = ''.join([args_string_map[k] for k, v in kwargs.items() if v])
    password = list(random.choice(chars) for i in range(length))

    if special_char:
        special_num = length // 16 + 1
        special_index = []
        for i in range(special_num):
            index = random.randint(1, length - 1)
            if index not in special_index:
                special_index.append(index)
        for i in special_index:
            password[i] = random.choice(symbols)

    password = ''.join(password)
    return password

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


def random_replace_char(s, chars, length):
    using_index = set()
    seq = list(s)

    while length > 0:
        index = secrets.randbelow(len(seq) - 1)
        if index in using_index or index == 0:
            continue
        seq[index] = secrets.choice(chars)
        using_index.add(index)
        length -= 1
    return ''.join(seq)


def remove_exclude_char(s, exclude_chars):
    for i in exclude_chars:
        s = s.replace(i, '')
    return s


def random_string(
        length: int, lower=True, upper=True, digit=True,
        special_char=False, exclude_chars='', symbols=string_punctuation
):
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
    chars = remove_exclude_char(chars, exclude_chars)
    texts = list(secrets.choice(chars) for __ in range(length))
    texts = ''.join(texts)

    # 控制一下特殊字符的数量, 别随机出来太多
    if special_char:
        symbols = remove_exclude_char(symbols, exclude_chars)
        symbol_num = length // 16 + 1
        texts = random_replace_char(texts, symbols, symbol_num)
    return texts

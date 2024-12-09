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


def random_replace_char(seq, chars, length):
    using_index = set()

    while length > 0:
        index = secrets.randbelow(len(seq) - 1)
        if index in using_index or index == 0:
            continue
        seq[index] = secrets.choice(chars)
        using_index.add(index)
        length -= 1
    return seq


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

    char_list = []
    if lower:

        lower_chars = remove_exclude_char(string.ascii_lowercase, exclude_chars)
        if not lower_chars:
            raise ValueError('After excluding characters, no lowercase letters are available.')
        char_list.append(lower_chars)

    if upper:
        upper_chars = remove_exclude_char(string.ascii_uppercase, exclude_chars)
        if not upper_chars:
            raise ValueError('After excluding characters, no uppercase letters are available.')
        char_list.append(upper_chars)

    if digit:
        digit_chars = remove_exclude_char(string.digits, exclude_chars)
        if not digit_chars:
            raise ValueError('After excluding characters, no digits are available.')
        char_list.append(digit_chars)

    secret_chars = [secrets.choice(chars) for chars in char_list]

    all_chars = ''.join(char_list)

    remaining_length = length - len(secret_chars)
    seq = [secrets.choice(all_chars) for _ in range(remaining_length)]

    if special_char:
        special_chars = remove_exclude_char(symbols, exclude_chars)
        if not special_chars:
            raise ValueError('After excluding characters, no special characters are available.')
        symbol_num = length // 16 + 1
        seq = random_replace_char(seq, symbols, symbol_num)
    secret_chars += seq

    secrets.SystemRandom().shuffle(secret_chars)
    return ''.join(secret_chars)

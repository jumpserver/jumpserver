import re


def no_special_chars(s):
    return bool(re.match(r'\w+$', s))

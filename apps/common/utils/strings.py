import re


def no_special_chars(s):
    return bool(re.match(r'\w+$', s))


def safe_str(s):
    return s.encode('utf-8', errors='ignore').decode('utf-8')

import re


def no_special_chars(s):
    """
    支持 常规字符及特殊符号 如: 0-9a-zA-Z!@#$%^&.*()_+-=[],.{}<>`~\|/?;:'"
    """
    return bool(re.match(r'[!@#$%^&.*()+-=\[\],.{}<>`~|/?;:\'"\\\w]+$', s))

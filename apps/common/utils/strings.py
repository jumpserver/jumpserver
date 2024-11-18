import difflib
import re


def no_special_chars(s):
    return bool(re.match(r'\w+$', s))


def safe_str(s):
    return s.encode('utf-8', errors='ignore').decode('utf-8')


def get_text_diff(old_text, new_text):
    diff = difflib.unified_diff(
        old_text.splitlines(), new_text.splitlines(), lineterm=""
    )
    return "\n".join(diff)


def color_fmt(msg, color=None):
    # ANSI 颜色代码
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'purple': '\033[95m',
        'cyan': '\033[96m',
        'default': '\033[0m'  # 结束颜色的默认值
    }

    # 获取颜色代码，如果没有指定颜色或颜色不支持，使用默认颜色
    color_code = colors.get(color, colors['default'])
    # 打印带颜色的消息
    return f"{color_code}{msg}{colors['default']}"  # 确保在消息结束后重置颜色


def color_print(msg, color=None):
    print(color_fmt(msg, color))


def color_fill_print(tmp, msg, color=None):
    text = tmp.format(color_fmt(msg, color))
    print(text)

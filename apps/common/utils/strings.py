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

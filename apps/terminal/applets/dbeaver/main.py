import sys

from common import (block_input, unblock_input)
from common import convert_base64_to_dict
from app import AppletApplication


def main():
    base64_str = sys.argv[1]
    data = convert_base64_to_dict(base64_str)
    applet_app = AppletApplication(**data)
    block_input()
    applet_app.run()
    unblock_input()
    applet_app.wait()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)

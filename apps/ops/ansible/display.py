# -*- coding: utf-8 -*-
#

import sys


class TeeObj:
    origin_stdout = sys.stdout

    def __init__(self, file_obj):
        self.file_obj = file_obj

    def write(self, msg):
        self.origin_stdout.write(msg)
        self.file_obj.write(msg.replace('*', ''))

    def flush(self):
        self.origin_stdout.flush()
        self.file_obj.flush()

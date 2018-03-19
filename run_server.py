#!/usr/bin/env python3
# coding: utf-8

import sys
import subprocess


if __name__ == '__main__':
    subprocess.call('python3 jms start all', shell=True,
                    stdin=sys.stdin, stdout=sys.stdout)


#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import sys
import os

# reload(sys)
# sys.setdefaultencoding('utf8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'apps'))

import re
import time
import datetime
import textwrap
import getpass
import readline
import django
import paramiko
import errno
import pyte
import operator
import struct, fcntl, signal, socket, select
from io import open as copen
import uuid


os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'



#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging
from logging.config import dictConfig
from ssh_config import config, env


CONFIG_SSH_SERVER = config.get(env)


def get_logger(name):
    dictConfig(CONFIG_SSH_SERVER.LOGGING)
    return logging.getLogger('jumpserver.%s' % name)


class ControlChar:
    CHARS = {
        'clear': '\x1b[H\x1b[2J',
    }

    def __init__(self):
        pass

    def __getattr__(self, item):
        return self.__class__.CHARS.get(item, '')


class SSHServerException(Exception):
    pass


control_char = ControlChar()

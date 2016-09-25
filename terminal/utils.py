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



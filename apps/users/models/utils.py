#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

from .user import User
from .group import UserGroup


def init_model():
    for cls in [User, UserGroup]:
        if getattr(cls, 'initial'):
            cls.initial()


def generate_fake():
    for cls in [User, UserGroup]:
        if getattr(cls, 'generate_fake'):
            cls.generate_fake()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

from . import User, UserGroup


def initial_model():
    for cls in [User, UserGroup]:
        cls.initial()


def generate_fake():
    for cls in [User, UserGroup]:
        cls.generate_fake()


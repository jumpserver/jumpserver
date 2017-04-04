#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from . import IDC, SystemUser, AdminUser, AssetGroup, Asset

__all__ = ['init_model', 'generate_fake']


def init_model():
    for cls in [IDC, SystemUser, AdminUser, AssetGroup, Asset]:
        if hasattr(cls, 'initial'):
            cls.initial()


def generate_fake():
    for cls in [IDC, SystemUser, AdminUser, AssetGroup, Asset]:
        if hasattr(cls, 'generate_fake'):
            cls.generate_fake()


if __name__ == '__main__':
    pass

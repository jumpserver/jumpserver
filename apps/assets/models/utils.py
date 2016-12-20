#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from . import IDC, SystemUser, AdminUser, AssetGroup, Asset, Tag

__all__ = ['initial', 'generate_fake']


def initial():
    for cls in [IDC, SystemUser, AdminUser, AssetGroup, Asset, Tag]:
        if hasattr(cls, 'initial'):
            cls.initial()


def generate_fake():
    for cls in [IDC, SystemUser, AdminUser, AssetGroup, Asset, Tag]:
        if hasattr(cls, 'generake_fake'):
            cls.generake_fake()


if __name__ == '__main__':
    pass

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

"""
兼容Python版本
"""

import sys

is_py2 = (sys.version_info[0] == 2)
is_py3 = (sys.version_info[0] == 3)


try:
    import simplejson as json
except (ImportError, SyntaxError):
    import json


if is_py2:

    def to_bytes(data):
        """若输入为unicode， 则转为utf-8编码的bytes；其他则原样返回。"""
        if isinstance(data, unicode):
            return data.encode('utf-8')
        else:
            return data

    def to_string(data):
        """把输入转换为str对象"""
        return to_bytes(data)

    def to_unicode(data):
        """把输入转换为unicode，要求输入是unicode或者utf-8编码的bytes。"""
        if isinstance(data, bytes):
            return data.decode('utf-8')
        else:
            return data

    def stringify(input):
        if isinstance(input, dict):
            return dict([(stringify(key), stringify(value)) for key,value in input.iteritems()])
        elif isinstance(input, list):
            return [stringify(element) for element in input]
        elif isinstance(input, unicode):
            return input.encode('utf-8')
        else:
            return input

    builtin_str = str
    bytes = str
    str = unicode


elif is_py3:

    def to_bytes(data):
        """若输入为str（即unicode），则转为utf-8编码的bytes；其他则原样返回"""
        if isinstance(data, str):
            return data.encode(encoding='utf-8')
        else:
            return data

    def to_string(data):
        """若输入为bytes，则认为是utf-8编码，并返回str"""
        if isinstance(data, bytes):
            return data.decode('utf-8')
        else:
            return data

    def to_unicode(data):
        """把输入转换为unicode，要求输入是unicode或者utf-8编码的bytes。"""
        return to_string(data)

    def stringify(input):
        return input

    builtin_str = str
    bytes = bytes
    str = str


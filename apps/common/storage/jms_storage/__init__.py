#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2018
#

__version__ = '0.0.59'

from importlib import import_module


_STORAGE_CLASSES = {
    'FTPStorage': 'ftp',
    'OSSStorage': 'oss',
    'OBSStorage': 'obs',
    'S3Storage': 's3',
    'AzureStorage': 'azure',
    'CEPHStorage': 'ceph',
    'JMSReplayStorage': 'jms',
    'JMSCommandStorage': 'jms',
    'MultiObjectStorage': 'multi',
    'SFTPStorage': 'sftp',
}
__all__ = [*_STORAGE_CLASSES, 'get_object_storage', 'get_multi_object_storage']


def __getattr__(name):
    module = _STORAGE_CLASSES.get(name)
    if module is None:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
    storage_class = getattr(import_module(f'.{module}', __name__), name)
    globals()[name] = storage_class
    return storage_class


def get_object_storage(config):
    storage_names = {
        's3': 'S3Storage', 'ceph': 'S3Storage', 'swift': 'S3Storage',
        'cos': 'S3Storage', 'oss': 'OSSStorage', 'server': 'JMSReplayStorage',
        'azure': 'AzureStorage', 'ftp': 'FTPStorage', 'obs': 'OBSStorage',
        'sftp': 'SFTPStorage',
    }
    name = storage_names.get(config.get('TYPE'), 'JMSReplayStorage')
    return __getattr__(name)(config)


def get_multi_object_storage(configs):
    return __getattr__('MultiObjectStorage')(configs)

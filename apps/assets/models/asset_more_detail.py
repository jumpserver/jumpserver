#!usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新增资产细节
"""

__author__ = 'LiTian'

import logging

from django.db import models

__all__ = ['AssetMoreDetail']
logger = logging.getLogger(__name__)


class AssetMoreDetail(models.Model):
    asset_id = models.ForeignKey("assets.Asset", on_delete=models.CASCADE, null=True)
    node = models.IntegerField(default=0, null=True)
    project = models.CharField(max_length=100, default='')
    manage = models.CharField(max_length=100, default='')
    app_path = models.CharField(max_length=100, default='')
    app_name = models.CharField(max_length=100, default='')
    app_data_path = models.CharField(max_length=100, default='')
    app_port = models.CharField(max_length=100, default='')
    broadband = models.CharField(max_length=100, default='')
    public_ip = models.CharField(max_length=100, default='')
    use_date = models.CharField(max_length=100, default='')
    status = models.CharField(max_length=100, default='')

    def __str__(self):
        return self.project


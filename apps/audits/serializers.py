# -*- coding: utf-8 -*-
#
from __future__ import absolute_import, unicode_literals
from rest_framework import serializers

from . import models


class ProxyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ProxyLog


class CommandLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CommandLog

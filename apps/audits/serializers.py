#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
from rest_framework import serializers

import models


class ProxyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ProxyLog


class CommandLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CommandLog




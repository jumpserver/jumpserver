#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import uuid

from django.db import models
from . import User


def get_uuid_string():
    return uuid.uuid4().__str__()


class AccessKey(models.Model):
    id = models.UUIDField(verbose_name='AccessKeyID', primary_key=True, default=get_uuid_string, editable=False)
    secret = models.UUIDField(verbose_name='AccessKeySecret', default=get_uuid_string, editable=False)
    user = models.ForeignKey(User, verbose_name='User')

    def __unicode__(self):
        return self.id

    __str__ = __unicode__

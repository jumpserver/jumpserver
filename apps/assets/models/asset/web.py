from django.db import models

from .common import Asset


class Web(Asset):
    autofill = models.CharField(max_length=16, default='basic')
    username_selector = models.CharField(max_length=128, blank=True, default='')
    password_selector = models.CharField(max_length=128, blank=True, default='')
    submit_selector = models.CharField(max_length=128, blank=True, default='')

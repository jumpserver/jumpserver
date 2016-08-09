from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group as AbstractGroup


class Group(AbstractGroup):
    comment = models.CharField(max_length=80, blank=True)


class User(AbstractUser):

    groups = models.ManyToManyField(Group)

    @property
    def name(self):
        return self.first_name + self.last_name

    class Meta:
        db_table = 'user'

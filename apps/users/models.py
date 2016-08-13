# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group as AbstractGroup


class Role(AbstractGroup):
    comment = models.CharField(max_length=80, blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'role'


class UserGroup(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='组名称', help_text='请输入组名称')
    comment = models.TextField(blank=True, verbose_name='描述', help_text='请输入用户组描述')
    date_added = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'usergroup'


class User(AbstractUser):
    groups = models.ManyToManyField(UserGroup)
    avatar = models.ImageField(verbose_name='头像', default='')
    wechat = models.CharField(max_length=30, verbose_name='微信')
    phone = models.CharField(max_length=20, verbose_name='手机')
    enable_2FA = models.BooleanField(default=False, verbose_name='启用二次验证')
    secret_key_2FA = models.CharField(max_length=16)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    private_key = models.CharField(max_length=5000)  # ssh key max length 4096 bit
    public_key = models.CharField(max_length=1000)
    created_by = models.CharField(max_length=30)
    date_expired = models.DateTimeField()

    @property
    def name(self):
        return self.first_name + self.last_name

    class Meta:
        db_table = 'user'

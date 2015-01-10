from django.db import models


class UserGroup(models.Model):
    name = models.CharField(max_length=80, unique=True)
    comment = models.CharField(max_length=160, blank=True, null=True)

    def __unicode__(self):
        return self.name


class User(models.Model):
    USER_ROLE_CHOICES = (
        ('SU', 'SuperUser'),
        ('GA', 'GroupAdmin'),
        ('CU', 'CommonUser'),
    )
    username = models.CharField(max_length=80, unique=True)
    password = models.CharField(max_length=100)
    name = models.CharField(max_length=80)
    email = models.EmailField(max_length=75, null=True, blank=True)
    role = models.CharField(max_length=2, choices=USER_ROLE_CHOICES, default='CU')
    user_group = models.ManyToManyField(UserGroup)
    ldap_pwd = models.CharField(max_length=100)
    ssh_key_pwd1 = models.CharField(max_length=100)
    ssh_key_pwd2 = models.CharField(max_length=100)
    ssh_pwd = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    last_login = models.IntegerField(default=0)
    date_joined = models.IntegerField()

    def __unicode__(self):
        return self.username

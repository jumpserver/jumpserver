from django.db import models


class Group(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __unicode__(self):
        return self.name


class User(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=100)
    key_pass = models.CharField(max_length=100)
    name = models.CharField(max_length=50)
    group = models.ManyToManyField(Group)
    is_admin = models.BooleanField()
    is_superuser = models.BooleanField()
    ldap_password = models.CharField(max_length=100, null=False)
    email = models.EmailField(max_length=50, null=True, blank=True)

    def __unicode__(self):
        return self.username


class Logs(models.Model):
    user = models.CharField(max_length=50)
    host = models.CharField(max_length=20)
    logfile = models.CharField(max_length=1000)
    finish = models.SmallIntegerField(max_length=4, default=0)
    start_time = models.IntegerField()
    end_time = models.IntegerField(default=0)

    def __unicode__(self):
        return self.logfile


class Pid(models.Model):
    pid = models.IntegerField()




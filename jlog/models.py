from django.db import models
from juser.models import User
import time


class Log(models.Model):
    user = models.CharField(max_length=20, null=True)
    host = models.CharField(max_length=200, null=True)
    remote_ip = models.CharField(max_length=100)
    login_type = models.CharField(max_length=100)
    log_path = models.CharField(max_length=100)
    start_time = models.DateTimeField(null=True)
    pid = models.IntegerField()
    is_finished = models.BooleanField(default=False)
    end_time = models.DateTimeField(null=True)
    filename = models.CharField(max_length=40)
    '''
    add by liuzheng
    '''
    # userMM = models.ManyToManyField(User)
    # logPath = models.TextField()
    # filename = models.CharField(max_length=40)
    # logPWD = models.TextField()  # log zip file's
    # nick = models.TextField(null=True)  # log's nick name
    # log = models.TextField(null=True)
    # history = models.TextField(null=True)
    # timestamp = models.IntegerField(default=int(time.time()))
    # datetimestamp = models.DateTimeField(auto_now_add=True)


    def __unicode__(self):
        return self.log_path


class Alert(models.Model):
    msg = models.CharField(max_length=20)
    time = models.DateTimeField(null=True)
    is_finished = models.BigIntegerField(default=False)


class TtyLog(models.Model):
    log = models.ForeignKey(Log)
    datetime = models.DateTimeField(auto_now=True)
    cmd = models.CharField(max_length=200)


class ExecLog(models.Model):
    user = models.CharField(max_length=100)
    host = models.TextField()
    cmd = models.TextField()
    remote_ip = models.CharField(max_length=100)
    result = models.TextField(default='')
    datetime = models.DateTimeField(auto_now=True)


class FileLog(models.Model):
    user = models.CharField(max_length=100)
    host = models.TextField()
    filename = models.TextField()
    type = models.CharField(max_length=20)
    remote_ip = models.CharField(max_length=100)
    result = models.TextField(default='')
    datetime = models.DateTimeField(auto_now=True)


class TermLog(models.Model):
    user = models.ManyToManyField(User)
    logPath = models.TextField()
    filename = models.CharField(max_length=40)
    logPWD = models.TextField()  # log zip file's
    nick = models.TextField(null=True)  # log's nick name
    log = models.TextField(null=True)
    history = models.TextField(null=True)
    timestamp = models.IntegerField(default=int(time.time()))
    datetimestamp = models.DateTimeField(auto_now_add=True)

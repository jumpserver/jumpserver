from django.db import models


class Log(models.Model):
    user = models.CharField(max_length=20, null=True)
    host = models.CharField(max_length=20, null=True)
    remote_ip = models.CharField(max_length=100)
    log_path = models.CharField(max_length=100)
    start_time = models.DateTimeField(null=True)
    pid = models.IntegerField(max_length=10)
    is_finished = models.BooleanField(default=False)
    end_time = models.DateTimeField(null=True)

    def __unicode__(self):
        return self.log_path


class Alert(models.Model):
    msg = models.CharField(max_length=20)
    time = models.DateTimeField(null=True)
    is_finished = models.BigIntegerField(default=False)


class TtyLog(models.Model):
    log = models.ForeignKey(Log)
    datetime = models.DateTimeField()
    cmd = models.CharField(max_length=200)


from django.db import models


class Server(models.Model):
    ip = models.CharField(max_length=16)
    username = models.CharField(max_length=20)
    password = models.CharField(max_length=30)
    port = models.IntegerField(max_length=5)
    sudo = models.BooleanField()

    def __unicode__(self):
        return self.ip
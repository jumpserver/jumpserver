from django.db import models


class User(models.Model):
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=100)
    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=50)

    def __unicode__(self):
        return self.username
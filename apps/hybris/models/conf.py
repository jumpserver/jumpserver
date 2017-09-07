from django.db import models

__all__ = ['HybrisConfig']


class HybrisConfig(models.Model):
    git_repo = models.CharField(max_length=1000, verbose_name='Git Repo')
    hybris_path = models.CharField(max_length=200, verbose_name='HybrisSourceZip')

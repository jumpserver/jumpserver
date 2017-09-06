from django.db import models


class HybrisConfig(models.Model):
    git_repo = models.CharField(max_length=1000, verbose_name='Git Repo')
    hybris_path = models.FilePathField(path='/usr/local', recursive=True, max_length=200, match='*.zip', verbose_name='HybrisSourceZip')

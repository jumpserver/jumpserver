# -*- coding: utf-8 -*-
#
from django.db import models
from django.shortcuts import redirect
from django.contrib.auth import get_user_model

from common.utils import get_logger
from .utils import get_current_org, get_model_by_db_table

logger = get_logger(__file__)


__all__ = ['OrgManager', 'OrgViewGenericMixin', 'OrgModelMixin']


class OrgManager(models.Manager):
    def get_queryset(self):
        print("GET CURR")
        current_org = get_current_org()
        kwargs = {}

        print("Get queryset ")
        print(current_org)

        if not current_org:
            return super().get_queryset().filter(**kwargs)
            kwargs['id'] = None
        elif current_org.is_real():
            kwargs['org'] = current_org
        elif current_org.is_default():
            kwargs['org'] = None
        queryset = super().get_queryset().filter(**kwargs)
        print(kwargs)
        print(queryset)
        return queryset


class OrgModelMixin(models.Model):
    org = models.ForeignKey('orgs.Organization', on_delete=models.PROTECT, null=True)
    objects = OrgManager()

    def save(self, *args, **kwargs):
        current_org = get_current_org()
        if current_org and current_org.is_real():
            self.org = current_org
        return super(OrgModelMixin, self).save(*args, **kwargs)

    class Meta:
        abstract = True


class OrgViewGenericMixin:
    def dispatch(self, request, *args, **kwargs):
        current_org = get_current_org()
        if not current_org:
            return redirect('orgs:switch-a-org')
        return super().dispatch(request, *args, **kwargs)

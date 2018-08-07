# -*- coding: utf-8 -*-
#
from threading import local

from django.db import models
from django.db.models import Q
from django.shortcuts import redirect
import warnings
from django.forms import ModelForm
from django.http.response import HttpResponseForbidden

from common.utils import get_logger
from .utils import current_org, set_current_org, set_to_root_org
from .models import Organization

logger = get_logger(__file__)
tl = local()

__all__ = [
    'OrgManager', 'OrgViewGenericMixin', 'OrgModelMixin', 'OrgModelForm',
    'RootOrgViewMixin',
]


class OrgManager(models.Manager):

    def get_queryset(self):
        queryset = super(OrgManager, self).get_queryset()
        kwargs = {}
        if not hasattr(tl, 'times'):
            tl.times = 0
        # logger.debug("[{}]>>>>>>>>>> Get query set".format(tl.times))
        if not current_org:
            kwargs['id'] = None
        elif current_org.is_real():
            kwargs['org_id'] = current_org.id
        elif current_org.is_default():
            queryset = queryset.filter(Q(org_id="") | Q(org_id__isnull=True))
        queryset = queryset.filter(**kwargs)
        tl.times += 1
        return queryset

    def all(self):
        if not current_org:
            msg = 'You can `objects.set_current_org(org).all()` then run it'
            return self
        else:
            return super(OrgManager, self).all()

    def set_current_org(self, org):
        if isinstance(org, str):
            org = Organization.objects.get(name=org)
        set_current_org(org)
        return self


class OrgModelMixin(models.Model):
    org_id = models.CharField(max_length=36, null=True, blank=True)
    objects = OrgManager()

    def save(self, *args, **kwargs):
        if current_org and current_org.is_real():
            self.org_id = current_org.id
        return super().save(*args, **kwargs)

    class Meta:
        abstract = True


class OrgViewGenericMixin:
    def dispatch(self, request, *args, **kwargs):
        print("Current org: {}".format(current_org))
        if not current_org:
            return redirect('orgs:switch-a-org')

        if not current_org.can_admin_by(request.user):
            print("{} cannot admin {}".format(request.user, current_org))
            if request.user.is_org_admin:
                print("Is org admin")
                return redirect('orgs:switch-a-org')
            return HttpResponseForbidden()
        else:
            print(current_org.can_admin_by(request.user))
        return super().dispatch(request, *args, **kwargs)


class RootOrgViewMixin:
    def dispatch(self, request, *args, **kwargs):
        set_to_root_org()
        return super().dispatch(request, *args, **kwargs)


class OrgModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'initial' not in kwargs:
            return
        for name, field in self.fields.items():
            if not hasattr(field, 'queryset'):
                continue
            model = field.queryset.model
            field.queryset = model.objects.all()


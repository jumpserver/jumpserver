# -*- coding: utf-8 -*-
#

from werkzeug.local import Local
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import redirect, get_object_or_404
from django.forms import ModelForm
from django.http.response import HttpResponseForbidden
from django.core.exceptions import ValidationError
from rest_framework import serializers

from common.utils import get_logger
from .utils import (
    current_org, set_current_org, set_to_root_org, get_current_org_id
)
from .models import Organization

logger = get_logger(__file__)
tl = Local()

__all__ = [
    'OrgManager', 'OrgViewGenericMixin', 'OrgModelMixin', 'OrgModelForm',
    'RootOrgViewMixin', 'OrgMembershipSerializerMixin',
    'OrgMembershipModelViewSetMixin', 'OrgResourceSerializerMixin',
]


class OrgManager(models.Manager):

    def get_queryset(self):
        queryset = super(OrgManager, self).get_queryset()
        kwargs = {}
        # if not hasattr(tl, 'times'):
        #     tl.times = 0
        # logger.debug("[{}]>>>>>>>>>> Get query set".format(tl.times))
        if not current_org:
            kwargs['id'] = None
        elif current_org.is_real():
            kwargs['org_id'] = current_org.id
        elif current_org.is_default():
            queryset = queryset.filter(org_id="")
        queryset = queryset.filter(**kwargs)
        # tl.times += 1
        return queryset

    def filter_by_fullname(self, fullname, field=None):
        ori_org = current_org
        value, org = self.model.split_fullname(fullname)
        set_current_org(org)
        if not field:
            if hasattr(self.model, 'name'):
                field = 'name'
            elif hasattr(self.model, 'hostname'):
                field = 'hostname'
        queryset = self.get_queryset().filter(**{field: value})
        set_current_org(ori_org)
        return queryset

    def get_object_by_fullname(self, fullname, field=None):
        queryset = self.filter_by_fullname(fullname, field=field)
        if len(queryset) == 1:
            return queryset[0]
        return None

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
    org_id = models.CharField(max_length=36, blank=True, default='', verbose_name=_("Organization"), db_index=True)
    objects = OrgManager()

    sep = '@'

    def save(self, *args, **kwargs):
        if current_org and current_org.is_real():
            self.org_id = current_org.id
        return super().save(*args, **kwargs)

    @classmethod
    def split_fullname(cls, fullname, sep=None):
        if not sep:
            sep = cls.sep
        index = fullname.rfind(sep)
        if index == -1:
            value = fullname
            org = Organization.default()
        else:
            value = fullname[:index]
            org = Organization.get_instance(fullname[index + 1:])
        return value, org

    @property
    def org(self):
        from orgs.models import Organization
        org = Organization.get_instance(self.org_id)
        return org

    @property
    def org_name(self):
        return self.org.name

    @property
    def fullname(self, attr=None):
        name = ''
        if attr and hasattr(self, attr):
            name = getattr(self, attr)
        elif hasattr(self, 'name'):
            name = self.name
        elif hasattr(self, 'hostname'):
            name = self.hostname
        if self.org.is_real():
            return name + self.sep + self.org_name
        else:
            return name

    def validate_unique(self, exclude=None):
        """
        Check unique constraints on the model and raise ValidationError if any
        failed.
        """
        self.org_id = current_org.id if current_org.is_real() else ''
        if exclude and 'org_id' in exclude:
            exclude.remove('org_id')
        unique_checks, date_checks = self._get_unique_checks(exclude=exclude)

        errors = self._perform_unique_checks(unique_checks)
        date_errors = self._perform_date_checks(date_checks)

        for k, v in date_errors.items():
            errors.setdefault(k, []).extend(v)

        if errors:
            raise ValidationError(errors)

    class Meta:
        abstract = True


class OrgViewGenericMixin:
    def dispatch(self, request, *args, **kwargs):
        if not current_org:
            return redirect('orgs:switch-a-org')

        if not current_org.can_admin_by(request.user):
            print("{} cannot admin {}".format(request.user, current_org))
            if request.user.is_org_admin:
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
        # if 'initial' not in kwargs:
        #     return
        for name, field in self.fields.items():
            if not hasattr(field, 'queryset'):
                continue
            model = field.queryset.model
            field.queryset = model.objects.all()


class OrgMembershipSerializerMixin:
    def run_validation(self, initial_data=None):
        initial_data['organization'] = str(self.context['org'].id)
        return super().run_validation(initial_data)


class OrgMembershipModelViewSetMixin:
    org = None
    membership_class = None
    lookup_field = 'user'
    lookup_url_kwarg = 'user_id'
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def dispatch(self, request, *args, **kwargs):
        self.org = get_object_or_404(Organization, pk=kwargs.get('org_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['org'] = self.org
        return context

    def get_queryset(self):
        queryset = self.membership_class.objects.filter(organization=self.org)
        return queryset


class OrgResourceSerializerMixin(serializers.Serializer):
    """
    通过API批量操作资源时, 自动给每个资源添加所需属性org_id的值为current_org_id
    (同时为serializer.is_valid()对Model的unique_together校验做准备)
    由于HiddenField字段不可读，API获取资产信息时获取不到org_id，
    但是coco需要资产的org_id字段，所以修改为CharField类型
    """
    org_id = serializers.CharField(default=get_current_org_id)

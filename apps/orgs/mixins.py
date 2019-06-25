# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import redirect, get_object_or_404
from django.forms import ModelForm
from django.http.response import HttpResponseForbidden
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from common.utils import get_logger
from common.validators import ProjectUniqueValidator
from common.mixins import BulkSerializerMixin
from .utils import (
    set_current_org, set_to_root_org, get_current_org, current_org,
    get_current_org_id_for_serializer,
)
from .models import Organization

logger = get_logger(__file__)

__all__ = [
    'OrgManager', 'OrgViewGenericMixin', 'OrgModelMixin', 'OrgModelForm',
    'RootOrgViewMixin', 'OrgMembershipSerializerMixin',
    'OrgMembershipModelViewSetMixin', 'OrgResourceSerializerMixin',
    'BulkOrgResourceSerializerMixin', 'BulkOrgResourceModelSerializer',
]


class OrgManager(models.Manager):

    def get_queryset(self):
        queryset = super(OrgManager, self).get_queryset()
        kwargs = {}
        _current_org = get_current_org()

        if _current_org is None:
            kwargs['id'] = None
        elif _current_org.is_real():
            kwargs['org_id'] = _current_org.id
        elif _current_org.is_default():
            queryset = queryset.filter(org_id="")

        queryset = queryset.filter(**kwargs)
        return queryset

    def all(self):
        _current_org = get_current_org()
        if _current_org is None:
            msg = 'You can `objects.set_current_org(org).all()` then run it'
            return self
        else:
            return super(OrgManager, self).all()

    def set_current_org(self, org):
        if isinstance(org, str):
            org = Organization.get_instance(org)
        set_current_org(org)
        return self


class OrgModelMixin(models.Model):
    org_id = models.CharField(max_length=36, blank=True, default='',
                              verbose_name=_("Organization"), db_index=True)
    objects = OrgManager()

    sep = '@'

    def save(self, *args, **kwargs):
        if current_org is not None and current_org.is_real():
            self.org_id = current_org.id
        return super().save(*args, **kwargs)

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

    class Meta:
        abstract = True


class OrgViewGenericMixin:
    def dispatch(self, request, *args, **kwargs):
        if current_org is None:
            return redirect('orgs:switch-a-org')

        if not current_org.can_admin_by(request.user):
            if request.user.is_org_admin:
                return redirect('orgs:switch-a-org')
            return HttpResponseForbidden()
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
    org_id = serializers.ReadOnlyField(default=get_current_org_id_for_serializer, label=_("Organization"))
    org_name = serializers.ReadOnlyField(label=_("Org name"))

    def get_validators(self):
        _validators = super().get_validators()
        validators = []

        for v in _validators:
            if isinstance(v, UniqueTogetherValidator) \
                    and "org_id" in v.fields:
                v = ProjectUniqueValidator(v.queryset, v.fields)
            validators.append(v)
        return validators

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(["org_id", "org_name"])
        return fields


class BulkOrgResourceSerializerMixin(OrgResourceSerializerMixin, BulkSerializerMixin):
    pass


class BulkOrgResourceModelSerializer(BulkOrgResourceSerializerMixin, serializers.ModelSerializer):
    pass

# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from common.serializers import CommonModelSerializer, \
    CommonBulkModelSerializer
from common.validators import ProjectUniqueValidator
from ..utils import get_current_org_id_for_serializer

__all__ = [
    "OrgResourceSerializerMixin", "BulkOrgResourceModelSerializer",
    "OrgResourceModelSerializerMixin",
]


class OrgResourceSerializerMixin(serializers.Serializer):
    """
    通过API批量操作资源时, 自动给每个资源添加所需属性org_id的值为current_org_id
    (同时为serializer.is_valid()对Model的unique_together校验做准备)
    由于HiddenField字段不可读，API获取资产信息时获取不到org_id，
    但是coco需要资产的org_id字段，所以修改为CharField类型
    """
    org_id = serializers.ReadOnlyField(default=get_current_org_id_for_serializer, label=_("Organization"))
    org_name = serializers.ReadOnlyField(label=_("Org name"))
    add_org_fields = True

    def get_validators(self):
        _validators = super().get_validators()
        validators = []

        for v in _validators:
            if isinstance(v, UniqueTogetherValidator) and "org_id" in v.fields:
                v = ProjectUniqueValidator(v.queryset, v.fields)
            validators.append(v)
        return validators

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        if self.add_org_fields:
            fields.extend(["org_id", "org_name"])
        return fields


class OrgResourceModelSerializerMixin(OrgResourceSerializerMixin, CommonModelSerializer):
    pass


class BulkOrgResourceModelSerializer(OrgResourceSerializerMixin, CommonBulkModelSerializer):
    pass

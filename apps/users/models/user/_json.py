from django.db import models
from django.db.models import Count


class JSONFilterMixin:
    @staticmethod
    def get_json_filter_attr_q(name, value, match):
        from rbac.models import RoleBinding
        from orgs.utils import current_org

        kwargs = {}
        if name == "system_roles":
            kwargs["scope"] = "system"
        elif name == "org_roles":
            kwargs["scope"] = "org"
            if not current_org.is_root():
                kwargs["org_id"] = current_org.id
        else:
            return None

        bindings = RoleBinding.objects.filter(**kwargs, role__in=value)
        if match == "m2m_all":
            user_id = (
                bindings.values("user_id")
                .annotate(count=Count("user_id")) # 这里不能有 distinct 会导致 count 不准确, acls 中过滤用户时会出现问题
                .filter(count=len(value))
                .values_list("user_id", flat=True)
            )
        else:
            user_id = bindings.values_list("user_id", flat=True)
        return models.Q(id__in=user_id)


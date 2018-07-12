# -*- coding: utf-8 -*-
#
from django.db import models

from common.utils import get_logger
from .utils import get_current_org, get_model_by_db_table

logger = get_logger(__file__)


class OrgQuerySet(models.QuerySet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class OrgManager(OrgQuerySet.as_manager().__class__):
    def get_queryset(self):
        current_org = get_current_org()
        kwargs = {}

        if not current_org:
            kwargs['id'] = None
        elif current_org.is_real:
            kwargs['org'] = current_org
        elif current_org.is_default():
            kwargs['org'] = None
        print("GET QUWRYSET ")
        print(kwargs)
        return super().get_queryset().filter(**kwargs)


class OrgModelMixin(models.Model):
    org = models.ForeignKey('orgs.Organization', on_delete=models.PROTECT, null=True)

    objects = OrgManager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _do_update(self, base_qs, using, pk_val, values, update_fields, forced_update):
        current_org = get_current_org()

        if current_org and current_org.is_real():
            kwargs = {'org': current_org}
            base_qs = base_qs.filter(**kwargs)
        else:
            logger.warn(
                'Attempting to update %s instance "%s" without a current tenant '
                'set. This may cause issues in a partitioned environment. '
                'Recommend calling set_current_org() before performing this '
                'operation.', self._meta.model.__name__, self
            )
        return super()._do_update(base_qs, using, pk_val, values, update_fields, forced_update)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        current_org = get_current_org()
        if current_org and not current_org.is_real():
            self.org = current_org
        return super().save(force_insert=force_insert, force_update=force_update,
                            using=using, update_fields=update_fields)

    class Meta:
        abstract = True

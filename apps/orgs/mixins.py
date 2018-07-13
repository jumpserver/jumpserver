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
        current_org = get_current_org()
        user_model = get_user_model()
        kwargs = {}

        print("Get queryset ")
        print(self.model)
        print(current_org)

        if not current_org:
            kwargs['id'] = None
        elif issubclass(self.model, user_model):
            kwargs['orgs'] = current_org
        elif current_org.is_real():
            kwargs['org'] = current_org
        elif current_org.is_default():
            kwargs['org'] = None
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
        user_model = get_user_model()
        current_org = get_current_org()
        if current_org and not current_org.is_real():
            self.org = current_org
        instance = super().save(
            force_insert=force_insert, force_update=force_update,
            using=using, update_fields=update_fields
        )
        if isinstance(instance, user_model):
            instance.orgs.add(current_org)
        return instance

    class Meta:
        abstract = True


class OrgViewGenericMixin:
    def dispatch(self, request, *args, **kwargs):
        current_org = get_current_org()
        if not current_org:
            return redirect('orgs:switch-a-org')
        return super().dispatch(request, *args, **kwargs)

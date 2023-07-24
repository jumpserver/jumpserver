from django.db.models import Model
from django.db.transaction import atomic
from django.utils.translation import gettext as _
from rest_framework import serializers

from orgs.utils import tmp_to_org
from tickets.models import Ticket

__all__ = ['DefaultPermissionName', 'get_default_permission_name', 'BaseApplyAssetSerializer']


def get_default_permission_name(ticket):
    name = ''
    if isinstance(ticket, Ticket):
        name = _('Created by ticket ({}-{})').format(ticket.title, str(ticket.id)[:4])
    return name


class DefaultPermissionName(object):
    default = None

    @staticmethod
    def _construct_default_permission_name(serializer_field):
        permission_name = ''
        ticket = serializer_field.root.instance
        if isinstance(ticket, Ticket):
            permission_name = get_default_permission_name(ticket)
        return permission_name

    def set_context(self, serializer_field):
        self.default = self._construct_default_permission_name(serializer_field)

    def __call__(self):
        return self.default


class BaseApplyAssetSerializer(serializers.Serializer):
    permission_model: Model

    @property
    def is_final_approval(self):
        instance = self.instance
        if not instance:
            return False
        if instance.approval_step == instance.ticket_steps.count():
            return True
        return False

    def filter_many_to_many_field(self, model, values: list, **kwargs):
        org_id = self.instance.org_id if self.instance else self.initial_data.get('org_id')
        ids = [instance.id for instance in values]
        with tmp_to_org(org_id):
            qs = model.objects.filter(id__in=ids, **kwargs).values_list('id', flat=True)
        return list(qs)

    def validate_apply_accounts(self, accounts):
        if self.is_final_approval and not accounts:
            raise serializers.ValidationError(_('This field is required.'))
        return accounts

    def validate(self, attrs):
        attrs = super().validate(attrs)

        apply_date_start = attrs['apply_date_start'].strftime('%Y-%m-%d %H:%M:%S')
        apply_date_expired = attrs['apply_date_expired'].strftime('%Y-%m-%d %H:%M:%S')
        if apply_date_expired <= apply_date_start:
            error = _('The expiration date should be greater than the start date')
            raise serializers.ValidationError({'apply_date_expired': error})

        return attrs

    @atomic
    def create(self, validated_data):
        instance = super().create(validated_data)
        name = _('Created by ticket ({}-{})').format(instance.title, str(instance.id)[:4])
        org_id = instance.org_id
        with tmp_to_org(org_id):
            if not self.permission_model.objects.filter(name=name).exists():
                instance.apply_permission_name = name
                instance.save(update_fields=['apply_permission_name'])
                return instance
        raise serializers.ValidationError(_('Permission named `{}` already exists'.format(name)))

    @atomic
    def update(self, instance, validated_data):
        old_rel_snapshot = instance.get_local_snapshot()
        instance = super().update(instance, validated_data)
        instance.old_rel_snapshot = old_rel_snapshot
        return instance

from django.utils.translation import gettext as _
from rest_framework import serializers

from orgs.utils import tmp_to_org
__all__ = ['AssetRequestValidationMixin']


class AssetRequestValidationMixin:

    def filter_many_to_many_field(self, model, values: list, **kwargs):
        org_id = self.instance.org_id if self.instance else self.initial_data.get('org_id')
        ids = [getattr(instance, 'pk', instance) for instance in values]
        with tmp_to_org(org_id):
            qs = model.objects.filter(id__in=ids, **kwargs).values_list('id', flat=True)
        if len(qs) != len(set(ids)):
            raise serializers.ValidationError("Resources must belong to the selected organization.")
        return list(qs)

    def validate_apply_accounts(self, accounts):
        if not isinstance(accounts, list) or not accounts or any(not isinstance(a, str) or not a.strip() or len(a) > 128 for a in accounts):
            raise serializers.ValidationError(_('This field is required.'))
        return accounts

    def validate(self, attrs):
        attrs = super().validate(attrs)

        apply_date_start = attrs.get('apply_date_start')
        apply_date_expired = attrs.get('apply_date_expired')
        required_error = _('This field is required.')
        errors = {}
        if apply_date_start is None:
            errors['apply_date_start'] = required_error
        if apply_date_expired is None:
            errors['apply_date_expired'] = required_error
        if errors:
            raise serializers.ValidationError(errors)

        apply_date_start = apply_date_start.strftime('%Y-%m-%d %H:%M:%S')
        apply_date_expired = apply_date_expired.strftime('%Y-%m-%d %H:%M:%S')
        if apply_date_expired <= apply_date_start:
            error = _('The expiration date should be greater than the start date')
            raise serializers.ValidationError({'apply_date_expired': error})

        return attrs

    @staticmethod
    def _get_permission_name(ticket):
        name = _('Created by ticket ({}-{})').format(ticket.title, str(ticket.id)[:4])
        if len(name) > 128:
            name = name[:121] + '...' + name[-4:]
        return name

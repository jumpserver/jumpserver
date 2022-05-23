from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.utils.translation import gettext_lazy as _

from .common import Ticket

__all__ = ['ApplyAssetTicket']

asset_or_node_help_text = _("Select at least one asset or node")


class ApplyAssetTicket(Ticket):
    apply_permission_name = models.CharField(max_length=128, verbose_name=_('Apply name'))
    apply_nodes = models.ManyToManyField('assets.Node', verbose_name=_('Apply nodes'))
    apply_nodes_display = models.JSONField(verbose_name=_('Apply nodes display'), required=False)
    # 申请信息
    apply_assets = models.ManyToManyField('assets.Asset', verbose_name=_('Apply assets'))
    apply_assets_display = models.ListField(
        required=False, read_only=True, child=models.CharField(),
        verbose_name=_('Apply assets display'), allow_null=True,
        default=list
    )
    apply_system_users = models.ListField(
        required=True, allow_null=True, child=models.UUIDField(),
        verbose_name=_('Apply system users')
    )
    apply_system_users_display = models.ListField(
        required=False, read_only=True, child=models.CharField(),
        verbose_name=_('Apply assets display'), allow_null=True,
        default=list,
    )
    apply_actions = ActionsField(
        required=True, allow_null=True
    )
    apply_actions_display = models.ListField(
        required=False, read_only=True, child=models.CharField(),
        verbose_name=_('Apply assets display'), allow_null=True,
        default=list,
    )
    apply_date_start = models.DateTimeField(
        required=True, verbose_name=_('Date start'), allow_null=True,
    )
    apply_date_expired = models.DateTimeField(
        required=True, verbose_name=_('Date expired'), allow_null=True,
    )

    def validate_approve_permission_name(self, permission_name):
        if not isinstance(self.root.instance, Ticket):
            return permission_name

        with tmp_to_org(self.root.instance.org_id):
            already_exists = AssetPermission.objects.filter(name=permission_name).exists()
            if not already_exists:
                return permission_name

        raise models.ValidationError(_(
            'Permission named `{}` already exists'.format(permission_name)
        ))

    def validate(self, attrs):
        if not attrs.get('apply_nodes') and not attrs.get('apply_assets'):
            raise models.ValidationError({
                'apply_nodes': asset_or_node_help_text,
                'apply_assets': asset_or_node_help_text,
            })

        apply_date_start = attrs['apply_date_start'].strftime('%Y-%m-%d %H:%M:%S')
        apply_date_expired = attrs['apply_date_expired'].strftime('%Y-%m-%d %H:%M:%S')

        if apply_date_expired <= apply_date_start:
            error = _('The expiration date should be greater than the start date')
            raise models.ValidationError({'apply_date_expired': error})

        attrs['apply_date_start'] = apply_date_start
        attrs['apply_date_expired'] = apply_date_expired
        return attrs

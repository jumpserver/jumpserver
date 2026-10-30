from django.utils.translation import gettext
import ntpath
import posixpath
import re
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .permissions import base_access, executable_protocols


def path_module(protocol):
    return ntpath if protocol == 'winrm' else posixpath


def validate_path(path, *, windows=False):
    if windows:
        path = path.replace('/', '\\')
        parts = path[3:].rstrip('\\').split('\\')
        if (not re.match(r'^[a-zA-Z]:\\', path) or
                any(ord(c) < 32 or ord(c) == 127 for c in path) or
                any(c in path[2:] for c in ':*?"<>|[]') or
                any(part in ('.', '..') or part.endswith((' ', '.')) or
                    re.match(r'^(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])$',
                             part.split('.')[0].rstrip(' '), re.I)
                    for part in parts if part)):
            raise ValidationError(gettext('Use an absolute Windows drive path without device names, streams or wildcards.'))
        return ntpath.normpath(path)
    if (not path.startswith('/') or path.startswith('//') or '\\' in path or
            any(ord(c) < 32 or ord(c) == 127 for c in path) or
            any(part in ('.', '..') for part in path.split('/')) or any(c in path for c in '*?[]')):
        raise ValidationError(gettext('Use an absolute Linux path without wildcards or relative components.'))
    return posixpath.normpath(path)


def expires_at(ticket):
    instance = ticket.workflow_instance
    return instance.date_finished + timedelta(seconds=instance.context['duration'])


def validate_context(ticket, *, approved=False, user=None, remote_addr=None):
    from accounts.models import Account
    from assets.models import Asset
    from ops.models.job import match_rejected_login_asset_acl
    from perms.const import ActionChoices
    from perms.utils.asset_perm import PermAssetDetailUtil
    from perms.utils.permission import AssetPermissionUtil
    from types import SimpleNamespace

    instance = ticket.workflow_instance
    context = instance.context
    if (context.get('file_transfer_version') != 2 or instance.ticket_id != ticket.pk or
            str(instance.org_id) != str(ticket.org_id) or instance.applicant_id != ticket.applicant_id):
        raise PermissionDenied(gettext('Invalid file transfer approval.'))
    if user and user.pk != ticket.applicant_id:
        raise PermissionDenied(gettext('Only the applicant can execute or download this transfer.'))
    if approved and (ticket.state != 'approved' or ticket.status != 'closed' or instance.state != 'approved' or
                     not instance.date_finished or not instance.date_finished <= timezone.now() < expires_at(ticket)):
        raise PermissionDenied(gettext('No active file transfer approval.'))
    asset = Asset.objects.filter(pk=context['request']['asset'], org_id=ticket.org_id,
                                 is_active=True, platform__category='host', platform__type__in=['linux', 'windows']).first()
    if not asset or not ticket.applicant:
        raise PermissionDenied(gettext('The approved asset or applicant is no longer available.'))
    access = base_access(ticket.applicant, asset)
    snapshot = context['accounts'][0]
    account = Account.objects.filter(pk=snapshot['id'], asset=asset, is_active=True,
                                     username=snapshot['username'], secret_type=snapshot['secret_type']).first()
    protocol = context['transfer_protocol']
    if (not account or protocol not in executable_protocols(asset) or
            (protocol == 'winrm' and account.secret_type != 'password') or
            protocol not in access.get(str(account.pk), {}).get('protocols', [])):
        raise PermissionDenied(gettext('The approved account access changed.'))
    if (asset.address != context['transfer_address'] or
            not asset.protocols.filter(name=protocol, port=context['transfer_port']).exists()):
        raise PermissionDenied(gettext('The approved asset connection changed.'))
    if remote_addr is not None:
        blocked_asset, _ = match_rejected_login_asset_acl(ticket.applicant, [asset], account.username, ip=remote_addr)
        if blocked_asset:
            raise PermissionDenied(gettext('The connection is restricted by an access control rule.'))
    # Preserve explicit action exclusions while granting only this operation.
    permissions = list(AssetPermissionUtil().get_permissions_for_user_asset(ticket.applicant, asset))
    permissions = [p for p in permissions if protocol in p.protocols or 'all' in p.protocols]
    bit = {'upload': ActionChoices.upload, 'download': ActionChoices.download}[context['request']['direction']]
    extra = SimpleNamespace(accounts=[account.username], actions=bit,
                            date_expired=timezone.now() + timedelta(seconds=1))
    actions, _ = PermAssetDetailUtil.parse_alias_action_date_expire([*permissions, extra], asset)
    if not actions.get(account.username, 0) & bit:
        raise PermissionDenied(gettext('File transfer is excluded by the asset permission policy.'))
    return asset, account

from urllib.parse import urljoin

from django.conf import settings
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string

from common.utils import reverse as js_reverse
from notifications.notifications import UserMessage


class PermedAssetsWillExpireUserMsg(UserMessage):
    def __init__(self, user, assets):
        super().__init__(user)
        self.assets = assets

    def get_html_msg(self) -> dict:
        subject = _("You permed assets is about to expire")
        context = {
            'name': self.user.name,
            'items': [str(asset) for asset in self.assets],
            'item_type': _("permed assets"),
            'show_help': True
        }
        message = render_to_string('perms/_msg_permed_items_expire.html', context)
        return {
            'subject': subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        from assets.models import Asset
        user = User.objects.first()
        assets = Asset.objects.all()[:10]
        return cls(user, assets)


class AssetPermsWillExpireForOrgAdminMsg(UserMessage):

    def __init__(self, user, perms, org):
        super().__init__(user)
        self.perms = perms
        self.org = org

    def get_items_with_url(self):
        items_with_url = []
        for perm in self.perms:
            url = js_reverse(
                'perms:asset-permission-detail',
                kwargs={'pk': perm.id}, external=True,
                api_to_ui=True
            ) + f'?oid={perm.org_id}'
            items_with_url.append([perm.name, url])
        return items_with_url

    def get_html_msg(self):
        items_with_url = self.get_items_with_url()
        subject = _("Asset permissions is about to expire")
        context = {
            'name': self.user.name,
            'items_with_url': items_with_url,
            'item_type': _('asset permissions of organization {}').format(self.org)
        }
        message = render_to_string('perms/_msg_item_permissions_expire.html', context)
        return {
            'subject': subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        from perms.models import AssetPermission
        from orgs.models import Organization

        user = User.objects.first()
        perms = AssetPermission.objects.all()[:10]
        org = Organization.objects.first()
        return cls(user, perms, org)


class PermedAppsWillExpireUserMsg(UserMessage):
    def __init__(self, user, apps):
        super().__init__(user)
        self.apps = apps

    def get_html_msg(self) -> dict:
        subject = _("Your permed applications is about to expire")
        context = {
            'name': self.user.name,
            'item_type': _('permed applications'),
            'items': [str(app) for app in self.apps]
        }
        message = render_to_string('perms/_msg_permed_items_expire.html', context)
        return {
            'subject': subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        from applications.models import Application

        user = User.objects.first()
        apps = Application.objects.all()[:10]
        return cls(user, apps)


class AppPermsWillExpireForOrgAdminMsg(UserMessage):
    def __init__(self, user, perms, org):
        super().__init__(user)
        self.perms = perms
        self.org = org

    def get_items_with_url(self):
        items_with_url = []
        perm_detail_url = urljoin(settings.SITE_URL, '/ui/#/perms/app-permissions/{}')
        for perm in self.perms:
            url = perm_detail_url.format(perm.id) + f'?oid={perm.org_id}'
            items_with_url.append([perm.name, url])
        return items_with_url

    def get_html_msg(self) -> dict:
        items = self.get_items_with_url()
        subject = _('Application permissions is about to expire')
        context = {
            'name': self.user.name,
            'item_type': _('application permissions of organization {}').format(self.org),
            'items_with_url': items
        }
        message = render_to_string('perms/_msg_item_permissions_expire.html', context)
        return {
            'subject': subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        from perms.models import ApplicationPermission
        from orgs.models import Organization

        user = User.objects.first()
        perms = ApplicationPermission.objects.all()[:10]
        org = Organization.objects.first()
        return cls(user, perms, org)

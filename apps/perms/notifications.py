import textwrap

from django.utils.translation import ugettext as _

from common.utils import reverse as js_reverse
from notifications.notifications import UserMessage


class BasePermMsg(UserMessage):
    @staticmethod
    def get_admin_content_template():
        message = textwrap.dedent(_("""
        Hello <b>%(name)s:<b><br>
        The following <b>%(item_type)s</b> will expire in 3 days
        <br><br>
        %(items)s
        """)).strip()
        return message

    def get_user_content_template(self):
        message = self.get_admin_content_template()
        message += _('<br>If you have any question, please contact the administrator')
        return message


class AssetPermWillExpireUserMsg(BasePermMsg):
    def __init__(self, user, assets):
        super().__init__(user)
        self.assets = assets

    def get_html_msg(self) -> dict:
        assets_text = '<br>'.join(str(asset) for asset in self.assets)
        subject = _("You permed assets is about to expire")
        template = self.get_user_content_template()
        message = template % {
            'name': self.user.name,
            'items': assets_text,
            'item_type': _("permed assets")
        }
        return {
            'subject': subject,
            'message': message
        }


class AssetPermWillExpireForOrgAdminMsg(BasePermMsg):
    def __init__(self, user, perms, org):
        super().__init__(user)
        self.perms = perms
        self.org = org

    def get_item_html(self):
        content = []
        item_template = '<a href={}>{}</a>'
        for perm in self.perms:
            url = js_reverse(
                'perms:asset-permission-detail',
                kwargs={'pk': perm.id}, external=True,
                api_to_ui=True
            ) + f'?oid={perm.org_id}'
            content.append(item_template.format(url, str(perm)))
        perms_text = '<br>'.join(content)
        return perms_text

    def get_html_msg(self):
        perms_html = self.get_item_html()
        subject = _("Asset permissions is about to expire")
        template = self.get_admin_content_template()
        message = template % {
            'name': self.user.name,
            'items': perms_html,
            'item_type': _('asset permissions of organization {}').format(self.org)
        }
        return {
            'subject': subject,
            'message': message
        }


class AppPermWillExpireUserMsg(BasePermMsg):
    def __init__(self, user, apps):
        super().__init__(user)
        self.apps = apps

    def get_html_msg(self) -> dict:
        apps_text = '<br>'.join(str(app) for app in self.apps)
        subject = _("Your permed applications is about to expire")
        template = self.get_user_content_template()
        message = template % {
            'name': self.user.name,
            'item_type': _('permed applications'),
            'items': apps_text
        }
        return {
            'subject': subject,
            'message': message
        }


class AppPermWillExpireForOrgAdminMsg(BasePermMsg):
    def __init__(self, user, perms, org):
        super().__init__(user)
        self.perms = perms
        self.org = org

    def get_items_html(self):
        content = []
        item_template = '<a href={}>{}</a>'
        for perm in self.perms:
            url = js_reverse(
                'perms:application-permission-detail',
                kwargs={'pk': perm.id},
                external=True,
                api_to_ui=True
            ) + f'?oid={perm.org_id}'
            content.append(item_template.format(url, str(perm)))
        perms_text = '<br>'.join(content)
        return perms_text

    def get_html_msg(self) -> dict:
        items = self.get_items_html()
        subject = _('Application permissions is about to expire')
        template = self.get_admin_content_template()
        message = template % {
            'name': self.user.name,
            'item_type': _('application permissions of organization {}').format(self.org),
            'items': items
        }
        return {
            'subject': subject,
            'message': message
        }

from datetime import datetime
from urllib.parse import urljoin

from django.utils.translation import ugettext as _
from django.conf import settings

from common.utils import reverse, get_request_ip_or_data, get_request_user_agent, lazyproperty
from notifications.notifications import UserMessage, SystemMessage


class AssetPermWillExpireMsg(UserMessage):
    def __init__(self, user, assets):
        super().__init__(user)
        self.assets = assets

    def get_html_msg(self) -> dict:
        user = self.user
        subject = _('Assets may expire')

        assets_text = ','.join(str(asset) for asset in self.assets)
        message = _("""
            Hello %(name)s:
            <br>
            Your permissions for the following assets may expire in three days:
            <br>
            %(assets)s
            <br>
            Please contact the administrator
        """) % {
            'name': user.name,
            'assets': assets_text
        }
        return {
            'subject': subject,
            'message': message
        }

    def get_text_msg(self) -> dict:
        user = self.user
        subject = _('Assets may expire')
        assets_text = ','.join(str(asset) for asset in self.assets)

        message = _("""
Hello %(name)s:
\n
Your permissions for the following assets may expire in three days:
\n
%(assets)s
\n
Please contact the administrator
        """) % {
            'name': user.name,
            'assets': assets_text
        }
        return {
            'subject': subject,
            'message': message
        }


class AssetPermWillExpireForOrgAdminMsg(UserMessage):
    def __init__(self, user, perms, org):
        super().__init__(user)
        self.perms = perms
        self.org = org

    def get_html_msg(self) -> dict:
        user = self.user
        subject = _('Asset permission will expired')
        perms_text = ','.join(str(perm) for perm in self.perms)

        message = _("""
            Hello %(name)s:
            <br>
            The following asset permissions of organization %(org) will expire in three days
            <br>
            %(perms)s
        """) % {
            'name': user.name,
            'org': self.org,
            'perms': perms_text
        }
        return {
            'subject': subject,
            'message': message
        }

    def get_text_msg(self) -> dict:
        user = self.user
        subject = _('Asset permission will expired')
        perms_text = ','.join(str(perm) for perm in self.perms)

        message = _("""
Hello %(name)s:
\n
The following asset permissions of organization %(org) will expire in three days
\n
%(perms)s
        """) % {
            'name': user.name,
            'org': self.org,
            'perms': perms_text
        }
        return {
            'subject': subject,
            'message': message
        }


class AssetPermWillExpireForAdminMsg(UserMessage):
    def __init__(self, user, org_perm_mapper: dict):
        super().__init__(user)
        self.org_perm_mapper = org_perm_mapper

    def get_html_msg(self) -> dict:
        user = self.user
        subject = _('Asset permission will expired')

        content = ''
        for org, perms in self.org_perm_mapper.items():
            content += f'<br> Orgnization: {org} <br> Permissions: {",".join(str(perm) for perm in perms)} <br>'

        message = _("""
            Hello %(name)s:
            <br>
            The following asset permissions will expire in three days
            <br>
            %(content)s
        """) % {
            'name': user.name,
            'content': content,
        }
        return {
            'subject': subject,
            'message': message
        }

    def get_text_msg(self) -> dict:
        user = self.user
        subject = _('Asset permission will expired')

        content = ''
        for org, perms in self.org_perm_mapper.items():
            content += f'\n Orgnization: {org} \n Permissions: {perms} \n'

        message = _("""
Hello %(name)s:
\n
The following asset permissions of organization %(org) will expire in three days
\n
%(content)s
        """) % {
            'name': user.name,
            'content': content,
        }
        return {
            'subject': subject,
            'message': message
        }


class AppPermWillExpireMsg(UserMessage):
    def __init__(self, user, apps):
        super().__init__(user)
        self.apps = apps

    def get_html_msg(self) -> dict:
        user = self.user
        subject = _('Applications may expire')

        apps_text = ','.join(str(app) for app in self.apps)
        message = _("""
            Hello %(name)s:
            <br>
            Your permissions for the following applications may expire in three days:
            <br>
            %(apps)s
            <br>
            Please contact the administrator
        """) % {
            'name': user.name,
            'apps': apps_text
        }
        return {
            'subject': subject,
            'message': message
        }

    def get_text_msg(self) -> dict:
        user = self.user
        subject = _('Applications may expire')
        apps_text = ','.join(str(app) for app in self.apps)

        message = _("""
Hello %(name)s:
\n
Your permissions for the following applications may expire in three days:
\n
%(apps)s
\n
Please contact the administrator
        """) % {
            'name': user.name,
            'apps': apps_text
        }
        return {
            'subject': subject,
            'message': message
        }


class AppPermWillExpireForOrgAdminMsg(UserMessage):
    def __init__(self, user, perms, org):
        super().__init__(user)
        self.perms = perms
        self.org = org

    def get_html_msg(self) -> dict:
        user = self.user
        subject = _('Application permission will expired')
        perms_text = ','.join(str(perm) for perm in self.perms)

        message = _("""
            Hello %(name)s:
            <br>
            The following application permissions of organization %(org) will expire in three days
            <br>
            %(perms)s
        """) % {
            'name': user.name,
            'org': self.org,
            'perms': perms_text
        }
        return {
            'subject': subject,
            'message': message
        }

    def get_text_msg(self) -> dict:
        user = self.user
        subject = _('Application permission will expired')
        perms_text = ','.join(str(perm) for perm in self.perms)

        message = _("""
Hello %(name)s:
\n
The following application permissions of organization %(org) will expire in three days
\n
%(perms)s
        """) % {
            'name': user.name,
            'org': self.org,
            'perms': perms_text
        }
        return {
            'subject': subject,
            'message': message
        }


class AppPermWillExpireForAdminMsg(UserMessage):
    def __init__(self, user, org_perm_mapper: dict):
        super().__init__(user)
        self.org_perm_mapper = org_perm_mapper

    def get_html_msg(self) -> dict:
        user = self.user
        subject = _('Application permission will expired')

        content = ''
        for org, perms in self.org_perm_mapper.items():
            content += f'<br>Orgnization: {org} <br> Permissions: {",".join(str(perm) for perm in perms)} <br>'

        message = _("""
            Hello %(name)s:
            <br>
            The following application permissions will expire in three days
            <br>
            %(content)s
        """) % {
            'name': user.name,
            'content': content,
        }
        return {
            'subject': subject,
            'message': message
        }

    def get_text_msg(self) -> dict:
        user = self.user
        subject = _('Application permission will expired')

        content = ''
        for org, perms in self.org_perm_mapper.items():
            content += f'\n Orgnization: {org} \n Permissions: {perms} \n'

        message = _("""
Hello %(name)s:
\n
The following application permissions of organization %(org) will expire in three days
\n
%(content)s
        """) % {
            'name': user.name,
            'content': content,
        }
        return {
            'subject': subject,
            'message': message
        }

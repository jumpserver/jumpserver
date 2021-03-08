from django.utils.translation import ugettext as _
from .base import BaseHandler


class Handler(BaseHandler):

    # body
    def _construct_meta_body_of_open(self):
        apply_login_user = self.ticket.meta.get('apply_login_user')
        apply_login_asset = self.ticket.meta.get('apply_login_asset')
        apply_login_system_user = self.ticket.meta.get('apply_login_system_user')
        applied_body = '''{}: {},
            {}: {},
            {}: {}
        '''.format(
            _("Applied login user"), apply_login_user,
            _("Applied login asset"), apply_login_asset,
            _("Applied login system user"), apply_login_system_user,
        )
        return applied_body

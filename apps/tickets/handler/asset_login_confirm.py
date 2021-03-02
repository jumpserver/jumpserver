from django.utils.translation import ugettext as _
from .base import BaseHandler


class Handler(BaseHandler):

    # body
    def _construct_meta_body_of_open(self):
        apply_login_ip = self.ticket.meta.get('apply_login_asset_ip')
        apply_sys_username = self.ticket.meta.get('apply_sys_username')
        apply_login_datetime = self.ticket.meta.get('apply_login_datetime')
        applied_body = '''{}: {},
            {}: {},
            {}: {}
        '''.format(
            _("Applied login Asset IP"), apply_login_ip,
            _("Applied System Username"), apply_sys_username,
            _("Applied login datetime"), apply_login_datetime,
        )
        return applied_body

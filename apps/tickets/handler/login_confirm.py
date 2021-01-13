from django.utils.translation import ugettext as __
from .base import BaseHandler


class Handler(BaseHandler):

    def _construct_meta_body_of_open(self):
        apply_login_ip = self.ticket.meta.get('apply_login_ip')
        apply_login_city = self.ticket.meta.get('apply_login_city')
        apply_login_datetime = self.ticket.meta.get('apply_login_datetime')
        applied_body = '''{}: {},
            {}: {},
            {}: {}
        '''.format(
            __("Applied login IP"), apply_login_ip,
            __("Applied login city"), apply_login_city,
            __("Applied login datetime"), apply_login_datetime,
        )
        return applied_body

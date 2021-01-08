from django.utils.translation import ugettext as __


class ConstructBodyMixin:
    
    def construct_login_confirm_applied_body(self):
        apply_login_ip = self.meta.get('apply_login_ip')
        apply_login_city = self.meta.get('apply_login_city')
        apply_login_datetime = self.meta.get('apply_login_datetime')
        applied_body = '''{}: {},
            {}: {},
            {}: {}
        '''.format(
            __("Applied login IP"), apply_login_ip,
            __("Applied login city"), apply_login_city,
            __("Applied login datetime"), apply_login_datetime,
        )
        return applied_body

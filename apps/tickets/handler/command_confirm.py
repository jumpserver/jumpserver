from django.utils.translation import ugettext as _
from .base import BaseHandler


class Handler(BaseHandler):

    # body
    def _construct_meta_body_of_open(self):
        apply_run_user = self.ticket.meta.get('apply_run_user')
        apply_run_asset = self.ticket.meta.get('apply_run_asset')
        apply_run_system_user = self.ticket.meta.get('apply_run_system_user')
        apply_run_command = self.ticket.meta.get('apply_run_command')
        apply_from_session_id = self.ticket.meta.get('apply_from_session_id')
        apply_from_cmd_filter_rule_id = self.ticket.meta.get('apply_from_cmd_filter_rule_id')
        apply_from_cmd_filter_id = self.ticket.meta.get('apply_from_cmd_filter_id')

        applied_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {},
        '''.format(
            _("Applied run user"), apply_run_user,
            _("Applied run asset"), apply_run_asset,
            _("Applied run system user"), apply_run_system_user,
            _("Applied run command"), apply_run_command,
            _("Applied from session"), apply_from_session_id,
            _("Applied from command filter rules"), apply_from_cmd_filter_rule_id,
            _("Applied from command filter"), apply_from_cmd_filter_id,
        )
        return applied_body

from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger, reverse
from common.utils import get_logger
from notifications.notifications import UserMessage


logger = get_logger(__file__)


class AclWarnningMessage(UserMessage):

    def __init__(self, user, context):
        super().__init__(user)
        self.context = context  

    def get_html_msg(self) -> dict:
        asset = self.context.get('asset')
        self.context['asset_url'] = reverse(
            'assets:asset-detail', kwargs={'pk': asset.id},
            api_to_ui=True, external=True, is_console=True
        ) + '?oid={}'.format(asset.org_id)
        message = render_to_string('acl/_msg_command_warnning.html', self.context)
        return {
            'subject': _('Command acl warning: {}').format(self.context.get('run_command')),
            'message': message
        }

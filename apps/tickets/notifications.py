import json
from urllib.parse import urljoin

from django.conf import settings
from django.core.cache import cache
from django.forms import model_to_dict
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from common.db.encoder import ModelJSONFieldEncoder
from common.sdk.im.wecom import wecom_tool
from common.utils import get_logger, random_string, reverse
from notifications.notifications import UserMessage
from . import const
from .models import Ticket

logger = get_logger(__file__)


class BaseTicketMessage(UserMessage):
    title: ''
    ticket: Ticket
    content_title: str

    def get_ticket_detail_url(self, external=True):
        detail_url = const.TICKET_DETAIL_URL.format(
            id=str(self.ticket.id), type=self.ticket.type
        )
        if not external:
            return detail_url
        return urljoin(settings.SITE_URL, detail_url)

    @property
    def content_title(self):
        raise NotImplementedError

    @property
    def subject(self):
        raise NotImplementedError

    def get_html_context(self):
        return {'ticket_detail_url': self.get_ticket_detail_url()}

    def get_wecom_context(self):
        ticket_detail_url = wecom_tool.wrap_redirect_url(
            self.get_ticket_detail_url(external=False)
        )
        return {'ticket_detail_url': ticket_detail_url}

    def gen_html_string(self, **other_context):
        context = {
            'title': self.content_title, 'content': self.content,
        }
        context.update(other_context)
        message = render_to_string(
            'tickets/_msg_ticket.html', context
        )
        return {'subject': self.subject, 'message': message}

    def get_html_msg(self) -> dict:
        return self.gen_html_string(**self.get_html_context())

    def get_wecom_msg(self):
        message = self.gen_html_string(**self.get_wecom_context())
        return self.html_to_markdown(message)

    @classmethod
    def gen_test_msg(cls):
        return None

    @property
    def content(self):
        content = [
            {'title': _('Ticket basic info'), 'content': self.basic_items},
            {'title': _('Ticket applied info'), 'content': self.spec_items},
        ]
        return content

    def _get_fields_items(self, item_names):
        fields = self.ticket._meta._forward_fields_map
        json_data = json.dumps(model_to_dict(self.ticket), cls=ModelJSONFieldEncoder)
        data = json.loads(json_data)
        items = []

        for name in item_names:
            field = fields[name]
            item = {'name': name, 'title': field.verbose_name}
            value = self.ticket.get_field_display(name, field, data)
            if not value:
                continue
            item['value'] = value
            items.append(item)
        return items

    @property
    def basic_items(self):
        item_names = ['serial_num', 'title', 'type', 'state', 'org_id', 'applicant', 'comment']
        return self._get_fields_items(item_names)

    @property
    def spec_items(self):
        fields = self.ticket._meta.local_fields + self.ticket._meta.local_many_to_many
        excludes = ['ticket_ptr', 'flow']
        item_names = [field.name for field in fields if field.name not in excludes]
        return self._get_fields_items(item_names)


class TicketAppliedToAssigneeMessage(BaseTicketMessage):
    def __init__(self, user, ticket):
        self.token = random_string(32)
        self.ticket = ticket
        super().__init__(user)

    @property
    def content_title(self):
        return _('Your has a new ticket, applicant - {}').format(self.ticket.applicant)

    @property
    def subject(self):
        title = _('{}: New Ticket - {} ({})').format(
            self.ticket.applicant,
            self.ticket.title,
            self.ticket.get_type_display()
        )
        return title

    def get_ticket_approval_url(self, external=True):
        url = reverse('tickets:direct-approve', kwargs={'token': self.token})
        if not external:
            return url
        return urljoin(settings.SITE_URL, url)

    def get_html_context(self):
        context = super().get_html_context()
        context['ticket_approval_url'] = self.get_ticket_approval_url()
        data = {
            'ticket_id': self.ticket.id,
            'approver_id': self.user.id, 'content': self.content,
        }
        cache.set(self.token, data, 3600)
        return context

    @classmethod
    def gen_test_msg(cls):
        from .models import Ticket
        from users.models import User
        ticket = Ticket.objects.first()
        user = User.objects.first()
        return cls(user, ticket)


class TicketProcessedToApplicantMessage(BaseTicketMessage):
    def __init__(self, user, ticket, processor):
        self.ticket = ticket
        self.processor = processor
        super().__init__(user)

    @property
    def content_title(self):
        return _('Your ticket has been processed, processor - {}').format(str(self.processor))

    @property
    def subject(self):
        title = _('Ticket has processed - {} ({})').format(
            self.ticket.title, self.ticket.get_type_display()
        )
        return title

    @classmethod
    def gen_test_msg(cls):
        from .models import Ticket
        from users.models import User
        ticket = Ticket.objects.first()
        user = User.objects.first()
        processor = User.objects.last()
        return cls(user, ticket, processor)

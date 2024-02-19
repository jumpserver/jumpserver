# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.core.cache import cache
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import redirect, reverse
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView

from common.utils import get_logger, FlashMessageUtil
from common.exceptions import JMSException
from users.models import User
from orgs.utils import tmp_to_root_org
from tickets.const import TicketType
from tickets.errors import AlreadyClosed
from tickets.models import (
    Ticket, ApplyAssetTicket,
    ApplyLoginTicket, ApplyLoginAssetTicket, ApplyCommandTicket
)

logger = get_logger(__name__)

__all__ = ['TicketDirectApproveView']


class TicketDirectApproveView(TemplateView):
    template_name = 'tickets/approve_check_password.html'
    redirect_field_name = 'next'

    TICKET_SUB_MODEL_MAP = {
        TicketType.apply_asset: ApplyAssetTicket,
        TicketType.login_confirm: ApplyLoginTicket,
        TicketType.login_asset_confirm: ApplyLoginAssetTicket,
        TicketType.command_confirm: ApplyCommandTicket,
    }

    @property
    def message_data(self):
        return {
            'title': _('Ticket approval'),
            'error': _("This ticket does not exist, "
                       "the process has ended, or this link has expired"),
            'redirect_url': self.login_url,
            'auto_redirect': False
        }

    @property
    def login_url(self):
        return reverse('authentication:login') + '?admin=1'

    def redirect_message_response(self, **kwargs):
        message_data = self.message_data
        for key, value in kwargs.items():
            if isinstance(value, str):
                message_data[key] = value
        if message_data.get('message'):
            message_data.pop('error')
        redirect_url = FlashMessageUtil.gen_message_url(message_data)
        return redirect(redirect_url)

    @staticmethod
    def clear(token):
        cache.delete(token)

    def get_context_data(self, **kwargs):
        # 放入工单信息
        kwargs.update({
            'content': kwargs['ticket_info'].get('content', []),
            'prompt_msg': _('Click the button below to approve or reject'),
        })
        return super().get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        if not (settings.TICKETS_DIRECT_APPROVE or request.user.is_authenticated):
            direct_url = reverse('tickets:direct-approve', kwargs={'token': kwargs['token']})
            message_data = {
                'title': _('Ticket approval'),
                'message': _('After successful authentication, this ticket can be approved directly'),
                'redirect_url': f'{self.login_url}&{self.redirect_field_name}={direct_url}',
                'auto_redirect': True,
            }
            redirect_url = FlashMessageUtil.gen_message_url(message_data)
            return redirect(redirect_url)

        ticket_info = cache.get(kwargs['token'])
        if not ticket_info:
            return self.redirect_message_response(redirect_url=self.login_url)
        return super().get(request, ticket_info=ticket_info, *args, **kwargs)

    @staticmethod
    def get_user(request, ticket_info):
        user = request.user
        if not user.is_authenticated and settings.TICKETS_DIRECT_APPROVE:
            user_id = ticket_info.get('approver_id')
            user = User.objects.filter(id=user_id).first()
        return user

    def post(self, request, **kwargs):
        token = kwargs.get('token')
        action = request.POST.get('action')
        if action not in ['approve', 'reject']:
            msg = _('Illegal approval action')
            return self.redirect_message_response(error=str(msg))

        ticket_info = cache.get(token)
        if not ticket_info:
            return self.redirect_message_response(redirect_url=self.login_url)
        try:
            user = self.get_user(request, ticket_info)
            ticket_id = ticket_info.get('ticket_id')
            with tmp_to_root_org():
                ticket = Ticket.all().get(id=ticket_id)
                ticket_sub_model = self.TICKET_SUB_MODEL_MAP[ticket.type]
                ticket = ticket_sub_model.objects.get(id=ticket_id)
            if not ticket.has_current_assignee(user):
                raise JMSException(_("This user is not authorized to approve this ticket"))
            getattr(ticket, action)(user)
        except AlreadyClosed as e:
            self.clear(token)
            return self.redirect_message_response(error=str(e), redirect_url=self.login_url)
        except Exception as e:
            return self.redirect_message_response(error=str(e), redirect_url=self.login_url)

        self.clear(token)
        return self.redirect_message_response(message=_("Success"), redirect_url=self.login_url)

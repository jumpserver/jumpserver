# ~*~ coding: utf-8 ~*~

from django import template
from ..backends import get_terminal_command_store

register = template.Library()
command_store_dict = get_terminal_command_store()


@register.filter
def get_session_command_amount(session_id):
    amount = 0
    for name, store in command_store_dict.items():
        amount += store.count(session=str(session_id))
    return amount

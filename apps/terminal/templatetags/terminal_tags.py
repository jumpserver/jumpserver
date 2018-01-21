# ~*~ coding: utf-8 ~*~

from django import template
from ..backends import get_multi_command_store

register = template.Library()
command_store = get_multi_command_store()


@register.filter
def get_session_command_amount(session_id):
    return command_store.count(session=session_id)

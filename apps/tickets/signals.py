from django.dispatch import Signal

post_ticket_state_changed = Signal()
active_step = Signal()

post_or_update_change_ticket_flow_approval = Signal()

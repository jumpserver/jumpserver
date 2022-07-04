from django.utils.module_loading import import_string


def get_ticket_handler(ticket):
    handler_class_path = 'tickets.handlers.{}.Handler'.format(ticket.type)
    handler_class = import_string(handler_class_path)
    return handler_class(ticket=ticket)

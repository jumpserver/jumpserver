from django.utils.module_loading import import_string


def load_handler_class(path):
    return import_string(path)


def get_ticket_handler(ticket):
    handler_class_path = 'ticket.handler.{}.Handler'.format(ticket.type)
    handler_class = load_handler_class(handler_class_path)
    return handler_class(ticket=ticket)

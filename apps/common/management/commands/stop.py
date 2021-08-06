from .services.command import ServiceBaseCommand, Action


class Command(ServiceBaseCommand):
    help = 'Stop services'
    action = Action.stop.value

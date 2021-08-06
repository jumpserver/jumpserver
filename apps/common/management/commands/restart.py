from .services.command import ServiceBaseCommand, Action


class Command(ServiceBaseCommand):
    help = 'Restart services'
    action = Action.restart.value

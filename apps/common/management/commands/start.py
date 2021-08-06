from .services.command import ServiceBaseCommand, Action


class Command(ServiceBaseCommand):
    help = 'Start services'
    action = Action.start.value

from .services.command import ServiceBaseCommand, Action


class Command(ServiceBaseCommand):
    help = 'Show services status'
    action = Action.status.value

from .services.command import BaseActionCommand, Action


class Command(BaseActionCommand):
    help = 'Stop services'
    action = Action.stop.value

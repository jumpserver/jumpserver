from .services.command import BaseActionCommand, Action


class Command(BaseActionCommand):
    help = 'Restart services'
    action = Action.restart.value

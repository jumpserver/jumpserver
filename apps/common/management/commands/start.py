from .services.command import BaseActionCommand, Action


class Command(BaseActionCommand):
    help = 'Start services'
    action = Action.start.value

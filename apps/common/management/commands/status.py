from .services.command import BaseActionCommand, Action


class Command(BaseActionCommand):
    help = 'Show services status'
    action = Action.status.value

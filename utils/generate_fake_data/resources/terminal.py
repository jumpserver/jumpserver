from .base import FakeDataGenerator
from terminal.models import Command


class CommandGenerator(FakeDataGenerator):
    resource = 'command'

    def do_generate(self, batch, batch_size):
        Command.generate_fake(len(batch), self.org)


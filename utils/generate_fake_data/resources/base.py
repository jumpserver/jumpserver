#!/usr/bin/python

from random import seed
from itertools import islice

from orgs.models import Organization


class FakeDataGenerator:
    resource = 'Fake'

    def __init__(self, batch_size=100, org_id=None):
        self.batch_size = batch_size
        self.org = self.switch_org(org_id)
        seed()

    def switch_org(self, org_id):
        o = Organization.get_instance(org_id, default=True)
        if o:
            o.change_to()
        print('Current org is: {}'.format(o))
        return o

    def do_generate(self, batch, batch_size):
        raise NotImplementedError

    def pre_generate(self):
        pass

    def after_generate(self):
        pass

    def generate(self, count=100):
        self.pre_generate()
        counter = iter(range(count))
        created = 0
        while True:
            batch = list(islice(counter, self.batch_size))
            if not batch:
                break
            self.do_generate(batch, self.batch_size)
            from_size = created
            created += len(batch)
            print('Generate %s: %s-%s' % (self.resource, from_size, created))
        self.after_generate()
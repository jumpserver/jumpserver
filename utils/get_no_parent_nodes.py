#!/usr/bin/python
#

import os
import sys
import django


if os.path.exists('../apps'):
    sys.path.insert(0, '../apps')
elif os.path.exists('./apps'):
    sys.path.insert(0, './apps')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

from assets.models import *
from orgs.utils import Organization

Organization.root().change_to()

ns = Node.objects.all()

for i in ns:
    try:
        pkey = i.parent.key
    except:
        pkey = ''
    if i.parent_key != pkey and not i.key.isdigit():
        print("Node parent not found: {} -> {}".format(i.key, i.parent_key))


from django.test import TestCase

from django.contrib.sessions.backends import file, db, cache
from django.contrib.auth.views import login
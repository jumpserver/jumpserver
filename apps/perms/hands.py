# ~*~ coding: utf-8 ~*~
#

from django.db import models
from django.utils.translation import ugettext_lazy as _


from users.utils import AdminUserRequiredMixin
from users.models import User, UserGroup
from assets.models import Asset, AssetGroup, SystemUser



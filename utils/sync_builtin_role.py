#!/usr/bin/python
import os
import sys
import django

if os.path.exists('../apps'):
	sys.path.insert(0, '../apps')
elif os.path.exists('./apps'):
	sys.path.insert(0, './apps')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

from django.db import transaction


from django.utils.translation import gettext_noop
from rbac.builtin import BuiltinRole, PredefineRole, Scope, system_auditor_perms


system_security_admin_exclude_perms = (
    ('rbac', 'menupermission', 'view', 'jdmc'),
)

class JDMCBuiltinRole(BuiltinRole):
    system_auditor = PredefineRole(
        '2', gettext_noop('AuditAdmin'), Scope.system, system_auditor_perms
    )
    system_security_admin = PredefineRole(
        '8', gettext_noop('SecAdmin'), Scope.system, system_security_admin_exclude_perms, 'exclude'
    )


def sync_role():
    JDMCBuiltinRole.sync_to_db(show_msg=True)

if __name__ == '__main__':
    with transaction.atomic():
        sync_role()


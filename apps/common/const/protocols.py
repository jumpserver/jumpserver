from django.utils.translation import ugettext_lazy as _

from common.db.models import ChoiceSet


class Protocols(ChoiceSet):
    SSH = 'ssh', 'SSH'
    RDP = 'rdp', 'RDP'
    TELNET = 'telnet', 'Telnet'
    VNC = 'vnc', 'VNC'

    MYSQL = 'mysql', 'MySQL'
    ORACLE = 'oracle', 'Oracle'
    PGSQL = 'pgsql', 'PostgreSQL'

    K8S = 'kubernetes', 'Kubernetes'
    REMOTE_APP = 'remote_app', 'RemoteApp'
    WEB = 'web', 'Web'

from IPy import IP
from django.utils.timezone import now
from rest_framework.request import Request

from common.http import get_remote_ip
from users.models.user import User


def check_user_policies(user: User, request: Request):
    now_ = now()
    remote_ip = IP(get_remote_ip(request))

    login_policies = user.cached_login_policies
    if login_policies:
        for login_policy in login_policies:
            if not (login_policy.date_from < now_ < login_policy.date_to):
                continue

            for ip in login_policy.ips.split(','):
                if ip == '*':
                    break
                if ip and remote_ip in IP(ip.strip()):
                    break
            else:
                continue
            break
        else:
            return False

    return True

# ~*~ coding: utf-8 ~*~
import re

import time
from django.utils import timezone

from common.utils import get_logger, get_object_or_none
from .ansible import AdHocRunner
from .ansible.exceptions import AnsibleError
from .models import AdHocRunHistory
from assets.utils import get_assets_by_hostname_list

logger = get_logger(__file__)
UUID_PATTERN = re.compile(r'[0-9a-zA-Z\-]{36}')


def run_AdHoc():
    pass


def is_uuid(s):
    if UUID_PATTERN.match(s):
        return True
    else:
        return False


def asset_to_dict(asset):
    return asset.to_json()


def asset_to_dict_with_credential(asset):
    return asset._to_secret_json()


def system_user_to_dict_with_credential(system_user):
    return system_user._to_secret_json()


def get_hosts_with_admin(hostname_list):
    assets = get_assets_by_hostname_list(hostname_list)
    return [asset._to_secret_json for asset in assets]


def get_hosts(hostname_list):
    assets = get_assets_by_hostname_list(hostname_list)
    return [asset.to_json for asset in assets]


def get_run_user(name):
    from assets.models import SystemUser
    system_user = get_object_or_none(SystemUser, name=name)
    if system_user is None:
        return {}
    else:
        return system_user._to_secret_json()


def get_hosts_with_run_user(hostname_list, run_as):
    hosts_dict = get_hosts(hostname_list)
    system_user_dct = get_run_user(run_as)

    for host in hosts_dict:
        host.update(system_user_dct)
    return hosts_dict


def hosts_add_become(hosts, adhoc_data):
    if adhoc_data.become:
        become_data = {
            "become": {
                "method": adhoc_data.become_method,
                "user": adhoc_data.become_user,
                "pass": adhoc_data.become_pass,
            }
        }
        for host in hosts:
            host.update(become_data)
    return hosts


def run_adhoc(adhoc_data, **options):
    """
    :param adhoc_data: Instance of AdHocData
    :param options: ansible support option, like forks ...
    :return:
    """
    name = adhoc_data.subject.name
    hostname_list = adhoc_data.hosts
    if adhoc_data.run_as_admin:
        hosts = get_hosts_with_admin(hostname_list)
    else:
        hosts = get_hosts_with_run_user(hostname_list, adhoc_data.run_as)
        hosts_add_become(hosts, adhoc_data)  # admin user 自带become

    runner = AdHocRunner(hosts)
    for k, v in options:
        runner.set_option(k, v)

    record = AdHocRunHistory(adhoc=adhoc_data)
    time_start = time.time()
    try:
        result = runner.run(adhoc_data.tasks, adhoc_data.pattern, name)
        record.is_finished = True
        if result.results_summary.get('dark'):
            record.is_success = False
        else:
            record.is_success = True
        record.result = result.results_raw
        record.summary = result.results_summary
        return result
    except AnsibleError as e:
        logger.error("Failed run adhoc {}, {}".format(name, e))
        raise
    finally:
        record.date_finished = timezone.now()
        record.timedelta = time.time() - time_start
        record.save()




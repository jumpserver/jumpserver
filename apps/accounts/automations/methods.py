import os
import copy

from accounts.const import AutomationTypes
from assets.automations.methods import get_platform_automation_methods


def copy_change_secret_to_push_account(methods):
    push_account = AutomationTypes.push_account
    change_secret = AutomationTypes.change_secret
    copy_methods = copy.deepcopy(methods)
    for method in copy_methods:
        if not method['id'].startswith(change_secret):
            continue
        copy_method = copy.deepcopy(method)
        copy_method['method'] = push_account.value
        copy_method['id'] = copy_method['id'].replace(
            change_secret, push_account
        )
        copy_method['name'] = copy_method['name'].replace(
            'Change secret', 'Push account'
        )
        methods.append(copy_method)
    return methods


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
automation_methods = get_platform_automation_methods(BASE_DIR)

platform_automation_methods = copy_change_secret_to_push_account(automation_methods)

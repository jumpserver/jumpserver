import os

from assets.automations.methods import get_platform_automation_methods

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
platform_automation_methods = get_platform_automation_methods(BASE_DIR)

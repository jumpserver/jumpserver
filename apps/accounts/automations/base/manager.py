from django.template.loader import render_to_string

from accounts.automations.methods import platform_automation_methods
from assets.automations.base.manager import BasePlaybookManager
from common.utils import get_logger

logger = get_logger(__name__)


class AccountBasePlaybookManager(BasePlaybookManager):
    template_path = ''

    @property
    def platform_automation_methods(self):
        return platform_automation_methods

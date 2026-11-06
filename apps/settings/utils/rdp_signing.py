import json
from contextlib import nullcontext

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from common.exceptions import JMSException
from common.utils import get_logger
from common.utils.rdp_signing import (
    get_rdp_signing_config, load_rdp_signing_material, replace_rdp_signing_files,
    RDP_SIGN_SETTING_NAMES, RDP_SIGN_UPLOAD_NAMES,
)
from settings.models import Setting


logger = get_logger(__name__)


class RDPSigningSaveError(JMSException):
    status_code = 503
    default_code = 'rdp_signing_save_failed'
    default_detail = _('Unable to save RDP signing files. Check certificate directory permissions and retry.')


def save_rdp_signing_settings(data, category):
    from settings.signal_handlers import publish_rdp_signing_config_changed

    try:
        with transaction.atomic():
            config = get_rdp_signing_config()
            Setting.objects.select_for_update().get_or_create(
                name='RDP_SIGN_ENABLED',
                defaults={'value': json.dumps(config['RDP_SIGN_ENABLED']), 'category': category},
            )
            for item in Setting.objects.filter(name__in=RDP_SIGN_SETTING_NAMES):
                config[item.name] = item.cleaned_value
            uploads = {name: data[name] for name in RDP_SIGN_UPLOAD_NAMES if data.get(name)}
            context = replace_rdp_signing_files(uploads) if uploads else nullcontext()
            with context:
                config['RDP_SIGN_ENABLED'] = data.get('RDP_SIGN_ENABLED', config['RDP_SIGN_ENABLED'])
                if config['RDP_SIGN_ENABLED']:
                    load_rdp_signing_material()
                for name in RDP_SIGN_SETTING_NAMES:
                    Setting.update_or_create(
                        name=name, value=config[name], category=category, encrypted=False, notify=False,
                    )
                transaction.on_commit(publish_rdp_signing_config_changed, robust=True)
            return config
    except Exception as error:
        logger.error('RDP signing settings save failed: error_type=%s', type(error).__name__)
        raise RDPSigningSaveError() from None

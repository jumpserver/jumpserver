import phonenumbers
import pycountry
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumbers import PhoneMetadata
from common.utils import lazyproperty

ADMIN = 'Admin'
USER = 'User'
AUDITOR = 'Auditor'


def get_country_phone_codes():
    phone_codes = []
    for region_code in phonenumbers.SUPPORTED_REGIONS:
        phone_metadata = PhoneMetadata.metadata_for_region(region_code)
        if phone_metadata:
            phone_codes.append((region_code, phone_metadata.country_code))
    return phone_codes


def get_country(region_code):
    country = pycountry.countries.get(alpha_2=region_code)
    if country:
        return country
    else:
        return None


def get_country_phone_choices():
    codes = get_country_phone_codes()
    choices = []
    for code, phone in codes:
        country = get_country(code)
        if not country:
            continue
        country_name = country.name
        flag = country.flag

        if country.name == 'China':
            country_name = _('China')

        if code == 'TW':
            country_name = 'Taiwan'
            flag = get_country('CN').flag
        choices.append({
            'name': country_name,
            'phone_code': f'+{phone}',
            'flag': flag,
            'code': code,
        })

    choices.sort(key=lambda x: x['name'])
    return choices


class Trigger(models.TextChoices):
    manual = 'manual', _('Manual')
    timing = 'timing', _('Timing')


class Status(models.TextChoices):
    ready = 'ready', _('Ready')
    pending = 'pending', _("Pending")
    running = 'running', _("Running")
    success = 'success', _("Success")
    failed = 'failed', _("Failed")
    error = 'error', _("Error")
    canceled = 'canceled', _("Canceled")


class Language(models.TextChoices):
    en = 'en', 'English'
    zh_hans = 'zh-hans', '中文(简体)'
    zh_hant = 'zh-hant', '中文(繁體)'
    ja = 'ja', '日本語',
    pt_br = 'pt-br', 'Português (Brasil)'

    @classmethod
    def get_code_mapper(cls):
        code_mapper = {code: code for code, name in cls.choices}
        code_mapper.update({
            'zh': cls.zh_hans.value,
            'zh-cn': cls.zh_hans.value,
            'zh-tw': cls.zh_hant.value,
            'zh-hk': cls.zh_hant.value,
        })
        return code_mapper

    @classmethod
    def to_internal_code(cls, code: str, default='en', with_filename=False):
        code_mapper = cls.get_code_mapper()
        code = code.lower()
        code = code_mapper.get(code) or code_mapper.get(default)
        if with_filename:
            cf_mapper = {
                cls.zh_hans.value: 'zh',
            }
            code = cf_mapper.get(code, code)
            code = code.replace('-', '_')
        return code

    @classmethod
    def get_other_codes(cls, code):
        code_mapper = cls.get_code_mapper()
        other_codes = [other_code for other_code, _code in code_mapper.items() if code == _code]
        return other_codes


class ConfirmOrIgnore(models.TextChoices):
    pending = '0', _('Pending')
    confirmed = '1', _('Confirmed')
    ignored = '2', _('Ignored')


COUNTRY_CALLING_CODES = get_country_phone_choices()


class LicenseEditionChoices(models.TextChoices):
    COMMUNITY = 'community', _('Community edition')
    BASIC = 'basic', _('Basic edition')
    STANDARD = 'standard', _('Standard edition')
    PROFESSIONAL = 'professional', _('Professional edition')
    ULTIMATE = 'ultimate', _('Ultimate edition')

    @staticmethod
    def from_key(key: str):
        for choice in LicenseEditionChoices:
            if choice == key:
                return choice
        return LicenseEditionChoices.COMMUNITY
    @staticmethod
    def parse_license_edition(info):
        count = info.get('license', {}).get('count', 0)

        if 50 >= count > 0:
            return LicenseEditionChoices.BASIC
        elif count <= 500:
            return LicenseEditionChoices.STANDARD
        elif count < 5000:
            return LicenseEditionChoices.PROFESSIONAL
        elif count >= 5000:
            return LicenseEditionChoices.ULTIMATE
        else:
            return LicenseEditionChoices.COMMUNITY

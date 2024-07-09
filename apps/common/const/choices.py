import phonenumbers
import pycountry
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumbers import PhoneMetadata

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
    manual = 'manual', _('Manual trigger')
    timing = 'timing', _('Timing trigger')


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
    jp = 'ja', '日本語',


COUNTRY_CALLING_CODES = get_country_phone_choices()

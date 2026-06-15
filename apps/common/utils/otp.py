# -*- coding: utf-8 -*-
#

import base64
import hashlib
import os

import pyotp
from django.conf import settings


def get_otp_digest():
    return hashlib.sha256 if settings.OTP_DIGEST == 'sha256' else hashlib.sha1


def normalize_otp_secret_key(otp_secret_key):
    if not otp_secret_key:
        return ''
    return str(otp_secret_key).replace(' ', '').upper()


def generate_otp_secret_key():
    return base64.b32encode(os.urandom(10)).decode('utf-8')


def generate_otp_uri(username, otp_secret_key=None, issuer="JumpServer"):
    otp_secret_key = normalize_otp_secret_key(otp_secret_key) or generate_otp_secret_key()
    totp = pyotp.TOTP(otp_secret_key, digest=get_otp_digest())
    otp_issuer_name = settings.OTP_ISSUER_NAME or issuer
    uri = totp.provisioning_uri(name=username, issuer_name=otp_issuer_name)
    return uri, otp_secret_key


def generate_otp_code(otp_secret_key):
    otp_secret_key = normalize_otp_secret_key(otp_secret_key)
    totp = pyotp.TOTP(otp_secret_key, digest=get_otp_digest())
    return totp.now()


def check_otp_code(otp_secret_key, otp_code):
    if not otp_secret_key or not otp_code:
        return False

    otp_secret_key = normalize_otp_secret_key(otp_secret_key)
    totp = pyotp.TOTP(otp_secret_key, digest=get_otp_digest())
    otp_valid_window = settings.OTP_VALID_WINDOW or 0
    return totp.verify(otp=str(otp_code), valid_window=otp_valid_window)


def is_otp_secret_key_valid(otp_secret_key):
    if not otp_secret_key:
        return True
    try:
        generate_otp_code(otp_secret_key)
    except Exception:
        return False
    return True

# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals
from six import string_types
from itertools import chain
import string
import logging
import datetime

from itsdangerous import Signer, TimedJSONWebSignatureSerializer, JSONWebSignatureSerializer, TimestampSigner, \
    BadSignature, SignatureExpired
from django.shortcuts import reverse as dj_reverse
from django.conf import settings
from django.core import signing
from django.utils import timezone

SECRET_KEY = settings.SECRET_KEY


def reverse(view_name, urlconf=None, args=None, kwargs=None, current_app=None, external=False):
    url = dj_reverse(view_name, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)

    if external:
        url = settings.SITE_URL.strip('/') + url
    return url


def get_object_or_none(model, **kwargs):
    try:
        obj = model.objects.get(**kwargs)
    except model.DoesNotExist:
        obj = None
    return obj


def encrypt(*args, **kwargs):
    try:
        return signing.dumps(*args, **kwargs)
    except signing.BadSignature:
        return ''


def decrypt(*args, **kwargs):
    try:
        return signing.loads(*args, **kwargs)
    except signing.BadSignature:
        return ''


def sign(value, secret_key=SECRET_KEY):
    signer = TimestampSigner(secret_key)
    return signer.sign(value)


def unsign(value, max_age=3600, secret_key=SECRET_KEY):
    signer = TimestampSigner(secret_key)
    try:
        return signer.unsign(value, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return ''


def date_expired_default():
    try:
        years = int(settings.CONFIG.DEFAULT_EXPIRED_YEARS)
    except TypeError:
        years = 70
    return timezone.now() + timezone.timedelta(days=365*years)


def sign(value):
    return SIGNER.sign(value)


def combine_seq(s1, s2, callback=None):
    for s in (s1, s2):
        if not hasattr(s, '__iter__'):
            return []

    seq = chain(s1, s2)
    if callback:
        seq = map(callback, seq)
    return seq


def search_object_attr(obj, value='', attr_list=None, ignore_case=False):
    """It's provide a method to search a object attribute equal some value

    If object some attribute equal :param: value, return True else return False

    class A():
        name = 'admin'
        age = 7

    :param obj: A object
    :param value: A string match object attribute
    :param attr_list: Only match attribute in attr_list
    :param ignore_case: Ignore case
    :return: Boolean
    """
    if value == '':
        return True

    try:
        object_attr = obj.__dict__
    except AttributeError:
        return False

    if attr_list is not None:
        new_object_attr = {}
        for attr in attr_list:
            new_object_attr[attr] = object_attr.pop(attr)
        object_attr = new_object_attr

    if ignore_case:
        if not isinstance(value, string_types):
            return False

        if value.lower() in map(string.lower, map(str, object_attr.values())):
            return True
    else:
        if value in object_attr.values():
            return True
    return False


def get_logger(name=None):
    return logging.getLogger('jumpserver.%s' % name)


def int_seq(seq):
    try:
        return map(int, seq)
    except ValueError:
        return seq


def timesince(dt, since='', default="just now"):
    """
    Returns string representing "time since" e.g.
    3 days, 5 hours.
    """

    if since is '':
        since = datetime.datetime.utcnow()

    if since is None:
        return default

    diff = since - dt

    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        if period:
            return "%d %s" % (period, singular if period == 1 else plural)
    return default


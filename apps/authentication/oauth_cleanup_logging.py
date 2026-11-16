"""Translate the cleanup totals emitted by django-oauth-toolkit.

Keep the toolkit's cleanup/retention implementation intact. The filter only
observes this invocation's thread and is always removed on exit.
"""
import logging
from threading import get_ident

from django.utils.translation import gettext, gettext_noop


class OAuthCleanupLog(logging.Filter):
    totals = {
        '%s Revoked refresh tokens deleted': gettext_noop('Revoked refresh tokens deleted'),
        '%s Orphaned refresh tokens deleted': gettext_noop('Orphaned refresh tokens deleted'),
        '%s Expired refresh tokens deleted': gettext_noop('Expired refresh tokens deleted'),
        '%s Expired access tokens deleted': gettext_noop('Expired access tokens deleted'),
        '%s Expired ID tokens deleted': gettext_noop('Expired ID tokens deleted'),
        '%s Expired grant tokens deleted': gettext_noop('Expired grant tokens deleted'),
    }
    disabled = {
        'refresh_revoked_at is %s. No revoked refresh tokens deleted.',
        'refresh_expire_at is %s. No expired refresh tokens deleted.',
    }

    def __init__(self, task_log):
        super().__init__()
        self.task_log = task_log
        self.thread = get_ident()
        self.logger = logging.getLogger('oauth2_provider.models')

    def __enter__(self):
        self.logger.addFilter(self)
        return self

    def __exit__(self, *args):
        self.logger.removeFilter(self)

    def filter(self, record):
        if get_ident() != self.thread:
            return True
        if record.msg in self.totals:
            count = record.args[0]
            self.task_log.checked += 1
            self.task_log.metric(gettext(self.totals[record.msg]), count)
            if count:
                self.task_log.processed += 1
            else:
                self.task_log.skip(gettext('No expired records in this credential category.'))
            return False
        if record.msg in self.disabled:
            self.task_log.checked += 1
            self.task_log.skip(gettext('Refresh-token retention settings require these tokens to be kept.'))
            return False
        return record.levelno >= logging.INFO

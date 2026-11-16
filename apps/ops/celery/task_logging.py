"""Consistent summaries for maintenance tasks, without logging task arguments."""
from collections import Counter

from django.utils.translation import gettext


class TaskLog:
    def __init__(self, logger, name):
        self.logger = logger
        self.name = name
        self.checked = 0
        self.processed = 0
        self.skips = Counter()
        self.failures = Counter()
        self.metrics = Counter()

    def __enter__(self):
        self.logger.info(gettext('Task started: %(name)s.'), {'name': self.name})
        return self

    def skip(self, reason, count=1):
        self.skips[str(reason)] += count

    def fail(self, reason, count=1):
        self.failures[str(reason)] += count

    def metric(self, name, count):
        self.metrics[str(name)] += count

    def delete(self, queryset, *, label=None):
        """Count matching targets separately from cascaded deletions."""
        matched = queryset.count()
        self.checked += matched
        result = queryset.delete()
        deleted = result[1].get(queryset.model._meta.label, 0)
        self.processed += deleted
        self.metric(label if label is not None else queryset.model._meta.verbose_name, deleted)
        if matched > deleted:
            self.skip(gettext('The record was already handled by another task.'), matched - deleted)
        return result

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            # Some callers are transactional: do not report rolled-back work
            # as completed. Celery retains the original exception traceback.
            self.logger.error(gettext(
                'Task interrupted after %(checked)s checks; changes may have been rolled back. '
                'See the task error for details.'
            ), {'checked': self.checked})
            return False
        if not (self.checked or self.processed or self.skips or self.failures):
            self.skip(gettext('No matching records to process.'), 0)
        self.logger.info(gettext(
            'Task summary: checked %(checked)s; processed %(processed)s; '
            'skipped %(skipped)s; failed %(failed)s.'
        ), {
            'checked': self.checked, 'processed': self.processed,
            'skipped': sum(self.skips.values()), 'failed': sum(self.failures.values()),
        })
        for name, count in self.metrics.items():
            self.logger.info(gettext('Result count — %(name)s: %(count)s.'), {'name': name, 'count': count})
        for reason, count in self.skips.items():
            if count:
                self.logger.info(gettext('Skipped %(count)s: %(reason)s'), {'count': count, 'reason': reason})
            else:
                self.logger.info(gettext('Reason: %(reason)s'), {'reason': reason})
        for reason, count in self.failures.items():
            self.logger.warning(gettext('Failed %(count)s: %(reason)s'), {'count': count, 'reason': reason})
        return False

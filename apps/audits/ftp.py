"""Read-only FTP origins derived from existing terminal sessions."""
from uuid import UUID

from django.db.models import CharField, Exists, OuterRef, Value
from django.db.models.functions import Cast, Lower, Replace
from django.utils.translation import gettext_lazy as _

from orgs.utils import tmp_to_root_org
from terminal.const import LoginFrom
from terminal.models import Session

FTP_CATEGORY_CHOICES = [('agent', _('Agent')), ('user', _('User operation')), ('unknown', _('Unknown'))]


def filter_ftp_category(queryset, category):
    # Compare normalized text: malformed references simply do not match. This
    # avoids per-log UUID regex/casts and permits a hash join for large counts.
    queryset = queryset.alias(ftp_session_ref=Lower(Replace('session', Value('-'), Value(''))))
    with tmp_to_root_org():
        sessions = Session.objects.alias(
            ftp_session_ref=Lower(Replace(Cast('pk', CharField()), Value('-'), Value(''))),
        ).filter(ftp_session_ref=OuterRef('ftp_session_ref'), org_id=OuterRef('org_id'))
        if category == 'agent':
            sessions = sessions.filter(login_from=LoginFrom.AG)
        elif category == 'user':
            sessions = sessions.filter(login_from__in=[value for value in LoginFrom.values if value != LoginFrom.AG])
        else:
            sessions = sessions.filter(login_from__in=LoginFrom.values)
    return queryset.filter(~Exists(sessions) if category == 'unknown' else Exists(sessions))


def ftp_log_sources(logs):
    """One indexed query per displayed/exported page, never one per file."""
    ids = {}
    for log in logs:
        try:
            reference = str(log.session).replace('-', '').lower()
            if len(reference) != 32:
                continue
            ids[log.pk] = UUID(hex=reference)
        except (ValueError, TypeError, AttributeError):
            continue
    if not ids:
        return {}
    with tmp_to_root_org():
        sessions = Session.objects.filter(pk__in=set(ids.values())).values_list('pk', 'org_id', 'login_from')
        sources = {(pk, str(org_id)): source for pk, org_id, source in sessions}
    return {log.pk: sources.get((ids.get(log.pk), str(log.org_id))) for log in logs}

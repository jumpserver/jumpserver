from django.utils.translation import gettext
import hashlib
import os
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from tickets.models import TicketTransferFile

MAX_FILES = 20


def size_limit():
    return min(max(int(settings.FILE_UPLOAD_SIZE_LIMIT_MB), 1), 1024) * 1024 * 1024


def valid_filename(name):
    return (bool(name) and len(name) <= 255 and name not in ('.', '..') and
            not any(c in name for c in '/\\') and not any(ord(c) < 32 or ord(c) == 127 for c in name))


def write_file(record, chunks):
    record.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    digest, size = hashlib.sha256(), 0
    try:
        with record.path.open('xb') as target:
            os.chmod(record.path, 0o600)
            for chunk in chunks:
                size += len(chunk)
                if size > size_limit():
                    raise ValidationError(gettext('File exceeds the transfer size limit.'))
                digest.update(chunk)
                target.write(chunk)
        record.size, record.sha256 = size, digest.hexdigest()
        record.save(update_fields=['size', 'sha256'])
    except BaseException:
        record.path.unlink(missing_ok=True)
        raise
    return record


def stage_upload(user, org_id, upload):
    from users.models import User
    if not valid_filename(upload.name) or upload.size > size_limit():
        raise ValidationError(gettext('Invalid file name or file exceeds the transfer size limit.'))
    with transaction.atomic():
        # Serialize a user's reservations so parallel uploads cannot bypass the quota.
        User.objects.select_for_update().get(pk=user.pk)
        files = TicketTransferFile.objects.filter(owner=user, org_id=org_id, purged_at__isnull=True)
        if files.count() >= MAX_FILES * 5:
            raise ValidationError(gettext('Too many retained ticket files. Wait for expired files to be cleaned up.'))
        record = TicketTransferFile.objects.create(owner=user, org_id=org_id, name=upload.name,
                                                   expires_at=timezone.now() + timedelta(hours=24))
    try:
        return write_file(record, upload.chunks())
    except BaseException:
        record.delete()
        raise


def reserve_download(ticket, name):
    from users.models import User
    from .policy import expires_at
    with transaction.atomic():
        User.objects.select_for_update().get(pk=ticket.applicant_id)
        retained = TicketTransferFile.objects.filter(owner=ticket.applicant, org_id=ticket.org_id,
                                                      purged_at__isnull=True)
        if retained.count() >= MAX_FILES * 5:
            from .transport import TransferError
            raise TransferError('storage_limit')
        return TicketTransferFile.objects.create(ticket=ticket, owner=ticket.applicant, org_id=ticket.org_id,
                                                 name=name, kind='download', expires_at=expires_at(ticket))


def claim_files(ticket):
    ids = ticket.request_data.get('files', [])
    records = list(TicketTransferFile.objects.select_for_update().filter(
        pk__in=ids, owner=ticket.applicant, org_id=ticket.org_id, ticket__isnull=True,
        kind='upload', purged_at__isnull=True, expires_at__gt=timezone.now(),
    ).order_by('id'))
    if len(records) != len(ids) or len({record.name for record in records}) != len(records):
        raise ValidationError(gettext('Files are missing, already submitted, or have duplicate names.'))
    for record in records:
        if not record.path.is_file():
            raise ValidationError(gettext('The uploaded file is no longer available.'))
        record.ticket = ticket
        record.expires_at = timezone.now() + timedelta(days=30)
        record.save(update_fields=['ticket', 'expires_at'])
    return [record.summary() for record in records]

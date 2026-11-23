import os
from datetime import timedelta
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import NotFound, ValidationError

from common.utils import get_logger
from tickets.models import TicketAttachment

logger = get_logger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx', '.xls', '.xlsx'}
IMAGE_TYPES = {'.jpg': ('JPEG', 'image/jpeg'), '.jpeg': ('JPEG', 'image/jpeg'), '.png': ('PNG', 'image/png')}


def validate_attachments(files):
    for upload in files:
        suffix = Path(upload.name).suffix.lower()
        if (not upload.name or len(upload.name) > 255 or any(c in upload.name for c in '/\\')
                or any(ord(c) < 32 or ord(c) == 127 for c in upload.name) or suffix not in EXTENSIONS):
            raise ValidationError(_('Supported attachments: JPG, PNG, PDF, Word and Excel.'))
        if not 0 < upload.size <= MAX_FILE_SIZE:
            raise ValidationError(_('Each attachment must be non-empty and no larger than 10 MB.'))
        upload.content_type = 'application/octet-stream'
        if suffix in IMAGE_TYPES:
            expected, content_type = IMAGE_TYPES[suffix]
            try:
                image = Image.open(upload)
                if image.format != expected:
                    raise ValueError('Image format does not match its extension')
                image.verify()
            except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
                raise ValidationError(_('Invalid attachment image.')) from exc
            finally:
                upload.seek(0)
            upload.content_type = content_type
    return files


def save_attachment(record, upload):
    record.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    size = 0
    with record.path.open('xb') as target:
        os.chmod(record.path, 0o600)
        for chunk in upload.chunks():
            size += len(chunk)
            if size > MAX_FILE_SIZE:
                raise ValidationError(_('Each attachment must be non-empty and no larger than 10 MB.'))
            target.write(chunk)
    record.size = size
    if not size:
        raise ValidationError(_('Each attachment must be non-empty and no larger than 10 MB.'))
    record.save()


def attachment_response(record):
    if record.expired:
        raise NotFound(_('This attachment has expired.'))
    try:
        response = FileResponse(
            record.path.open('rb'), filename=record.name,
            as_attachment=True,
            content_type=record.content_type,
        )
    except FileNotFoundError as exc:
        raise NotFound(_('This attachment is no longer available.')) from exc
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'no-store'
    return response


def cleanup_attachments():
    from orgs.utils import tmp_to_root_org
    cutoff = timezone.now() - timedelta(days=settings.TICKET_ATTACHMENT_RETENTION_DAYS)
    with tmp_to_root_org():
        expired = TicketAttachment.objects.filter(purged_at__isnull=True, date_created__lte=cutoff)
        for record in expired.iterator(chunk_size=200):
            try:
                record.path.unlink(missing_ok=True)
            except OSError:
                logger.exception('Failed to delete ticket attachment %s', record.pk)
                continue
            TicketAttachment.objects.filter(pk=record.pk).update(purged_at=timezone.now())

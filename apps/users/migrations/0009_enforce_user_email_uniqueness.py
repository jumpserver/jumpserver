import hashlib
import hmac
import json
import logging
import re

import common.db.fields
from common.db.utils import Encryptor
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import migrations, models, transaction


logger = logging.getLogger(__name__)


def email_lookup(email):
    # Freeze the lookup format used by this migration.
    return hmac.new(
        settings.SECRET_KEY.encode(), email.strip().lower().encode(), hashlib.sha256,
    ).hexdigest()


def replacement_address(email, user_id, occupied):
    suffix = f'.dup-{user_id.hex[:12]}'
    attempt = 0
    while True:
        counter = f'-{attempt}' if attempt else ''
        candidate = f'{email.strip()}{suffix}{counter}.invalid'
        try:
            validate_email(candidate)
            fits = len(candidate) <= 254
        except ValidationError:
            fits = False
        if not fits:
            candidate = f'duplicate-{user_id.hex}{counter}@email-conflict.invalid'
        lookup = email_lookup(candidate)
        if lookup not in occupied:
            return candidate, lookup
        attempt += 1


def warn_user_ids(message, ids):
    for offset in range(0, len(ids), 100):
        logger.warning('%s %s', message, ', '.join(map(str, ids[offset:offset + 100])))


def backfill_email_lookup(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Preference = apps.get_model('users', 'Preference')
    db = schema_editor.connection.alias
    users = User._base_manager.using(db)
    # Read the stored text so one unreadable email can be reported by user ID.
    stored_email = models.ExpressionWrapper(models.F('email'), output_field=models.TextField())
    rows = users.annotate(ciphertext=stored_email).order_by('date_joined', 'pk').values_list(
        'pk', 'ciphertext', 'email_lookup',
    )
    owners = {}
    duplicates = []
    unreadable = []
    lookup_updates = []
    for user_id, ciphertext, old_lookup in rows.iterator(chunk_size=1000):
        try:
            email = Encryptor(ciphertext).decrypt() if ciphertext else None
        except Exception:
            email = None
        if not isinstance(email, str) or '@' not in email:
            unreadable.append((user_id, old_lookup))
            continue
        lookup = email_lookup(email)
        if lookup in owners:
            duplicates.append((user_id, email, owners[lookup]))
        else:
            owners[lookup] = (user_id, email)
            if lookup != old_lookup:
                lookup_updates.append(User(pk=user_id, email_lookup=lookup))

    # Preserve recoverable lookup values and ciphertext if an address can't be read.
    occupied = set(owners)
    for user_id, old_lookup in unreadable:
        if old_lookup and re.fullmatch(r'[0-9a-f]{64}', old_lookup) and old_lookup not in occupied:
            occupied.add(old_lookup)
        else:
            lookup = f'unreadable:{user_id.hex}'
            if old_lookup != lookup:
                lookup_updates.append(User(pk=user_id, email_lookup=lookup))

    # All original addresses have been reserved before generating any replacements.
    for user_id, email, (keeper_id, keeper_email) in duplicates:
        candidate, lookup = replacement_address(email, user_id, occupied)
        occupied.add(lookup)
        users.filter(pk=user_id).update(email=candidate, email_lookup=lookup)
        # Capture the actual addresses before a retry or a subsequent user edit.
        repair = json.dumps({
            'keeper_id': str(keeper_id), 'keeper_email': keeper_email,
            'old_email': email, 'new_email': candidate,
        })
        Preference.objects.using(db).update_or_create(
            user_id=user_id, name='users_0009_duplicate_email',
            defaults={'category': 'migration', 'encrypted': True, 'value': Encryptor(repair).encrypt()},
        )
    for offset in range(0, len(lookup_updates), 1000):
        users.bulk_update(lookup_updates[offset:offset + 1000], ['email_lookup'], batch_size=1000)

    if duplicates or unreadable:
        def report():
            warn_user_ids('Duplicate email replaced with a .invalid address; review user IDs:',
                          [pk for pk, _, _ in duplicates])
            warn_user_ids('Invalid or unreadable email preserved; review user IDs:',
                          [pk for pk, _ in unreadable])
        transaction.on_commit(report, using=db)


class AddConstraintIfMissing(migrations.AddConstraint):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        connection = schema_editor.connection
        if not self.allow_migrate_model(connection.alias, model):
            return
        if not schema_editor.collect_sql:
            with connection.cursor() as cursor:
                constraints = connection.introspection.get_constraints(cursor, model._meta.db_table)
            existing = constraints.get(self.constraint.name)
            if existing is not None:
                columns = [model._meta.get_field(field).column for field in self.constraint.fields]
                if not existing.get('unique') or existing.get('columns') != columns:
                    raise RuntimeError(f'Existing constraint {self.constraint.name} has an unexpected definition.')
                return
        super().database_forwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0008_expand_user_email_storage'),
    ]

    operations = [
        migrations.RunPython(backfill_email_lookup, migrations.RunPython.noop, atomic=True),
        migrations.AlterField(
            model_name='user',
            name='email_lookup',
            field=models.CharField(max_length=128, verbose_name='Email lookup'),
        ),
        AddConstraintIfMissing(
            model_name='user',
            constraint=models.UniqueConstraint(
                fields=['email_lookup'], name='users_user_email_lookup_uniq',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=common.db.fields.EncryptCharField(
                max_length=256, storage_max_length=1536, verbose_name='Email',
            ),
        ),
    ]

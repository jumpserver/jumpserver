import hashlib
import hmac

import common.db.fields
from common.db.utils import Encryptor
from django.conf import settings
from django.db import migrations, models


def backfill_email_lookup(apps, schema_editor):
    User = apps.get_model('users', 'User')
    connection = schema_editor.connection
    quote = connection.ops.quote_name
    table = quote(User._meta.db_table)
    pk_column = quote(User._meta.pk.column)
    email_column = quote(User._meta.get_field('email').column)
    lookup_column = quote(User._meta.get_field('email_lookup').column)
    seen = {}
    updates = []
    problems = []
    problem_count = 0

    # Read ciphertext explicitly so a decryption failure can identify its user.
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT {pk_column}, {email_column}, {lookup_column} FROM {table}')
        while rows := cursor.fetchmany(1000):
            for user_id, ciphertext, old_lookup in rows:
                user_id = User._meta.pk.to_python(user_id)
                try:
                    email = Encryptor(ciphertext).decrypt() if ciphertext else ''
                    if not isinstance(email, str) or not email.strip() or '@' not in email:
                        raise ValueError
                    # Keep the existing strip/lower lookup contract without logging plaintext on errors.
                    lookup = hmac.new(
                        settings.SECRET_KEY.encode('utf-8'),
                        email.strip().lower().encode('utf-8'), hashlib.sha256,
                    ).hexdigest()
                except Exception:
                    problem = f'Invalid or undecryptable email: user {user_id}'
                else:
                    other_id = seen.get(lookup)
                    if other_id is not None:
                        problem = f'Duplicate normalized email: users {other_id}, {user_id}'
                    else:
                        seen[lookup] = user_id
                        if old_lookup != lookup:
                            updates.append(User(pk=user_id, email_lookup=lookup))
                        continue
                problem_count += 1
                if len(problems) < 20:
                    problems.append(problem)

    # Finish auditing before any writes, including on databases without transactional DDL.
    if problem_count:
        raise RuntimeError(
            'Cannot enforce user email uniqueness. Correct the affected users and retry; '
            'no user emails were changed. '
            + '; '.join(problems)
            + f'. Total conflicts: {problem_count}.'
        )
    # Historical models must not use the live manager's guarded email write methods.
    users = User._base_manager.using(connection.alias)
    for offset in range(0, len(updates), 1000):
        users.bulk_update(updates[offset:offset + 1000], ['email_lookup'], batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0008_expand_user_email_storage'),
    ]

    operations = [
        migrations.RunPython(backfill_email_lookup, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='email_lookup',
            field=models.CharField(max_length=128, verbose_name='Email lookup'),
        ),
        migrations.AddConstraint(
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

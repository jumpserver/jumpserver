import hashlib
import hmac
import logging
import re
import string
from collections import defaultdict
from uuid import UUID, uuid5

import common.db.fields
from common.db.utils import Encryptor
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import migrations, models, transaction


logger = logging.getLogger(__name__)
NOTICE_ID = UUID('01c1ba70-0ce8-57e1-90b3-f36017108a4e')
DELIVERY_ID = uuid5(NOTICE_ID, 'admin')

NOTICE_TEXT = {
    'zh': {
        'subject': '升级通知',
        'intro': '升级时发现重复邮箱。请点击“待处理”的用户，为其设置有效且唯一的邮箱。'
                 '当前 .invalid 临时邮箱无法接收邮件。',
        'original_email': '原邮箱',
        'group_count': '{count} 人',
        'kept': '已保留',
        'changed': '待处理',
        'new_email': '临时邮箱',
        'user_id': '用户 ID',
        'deleted_user': '已删除用户',
    },
    'en': {
        'subject': 'Upgrade Notice',
        'intro': 'Duplicate emails were found during the upgrade. Select the users marked '
                 '“Needs attention” and assign each a unique, valid email address. '
                 'The temporary .invalid addresses cannot receive email.',
        'original_email': 'Original email',
        'group_count': '{count} users',
        'kept': 'Retained',
        'changed': 'Needs attention',
        'new_email': 'Temporary email',
        'user_id': 'User ID',
        'deleted_user': 'Deleted user',
    },
}


# Markdown entities display as literal text, including inside link labels.
# User-supplied characters must never add links, line breaks or HTML to a notice.
MARKDOWN_TEXT = str.maketrans({
    char: f'&#{ord(char)};' for char in string.punctuation + '\r\n\t'
})


def user_paragraph(label, user_id, accounts, text):
    user = accounts.get(user_id)
    if user is None:
        identity = text['deleted_user']
    else:
        name = (user.name or user.username).translate(MARKDOWN_TEXT)
        username = user.username.translate(MARKDOWN_TEXT)
        identity = f'[{name}({username})](/ui/#/console/users/users/{user_id})'
    return f'{label}　{identity}  \n{text["user_id"]}　{user_id}'


def notification_body(groups, accounts, language='en'):
    text = NOTICE_TEXT[language]
    paragraphs = [text['intro']]
    for keeper_id, repairs in groups.items():
        original = repairs[0][1]['keeper_email']
        count = text['group_count'].format(count=len(repairs) + 1)
        group = [
            f'**{text["original_email"]}　{original.translate(MARKDOWN_TEXT)}（{count}）**',
            user_paragraph(text['kept'], keeper_id, accounts, text),
        ]
        for user_id, repair in repairs:
            paragraph = user_paragraph(text['changed'], user_id, accounts, text)
            old_email = repair['old_email']
            if old_email != original:
                paragraph += f'  \n{text["original_email"]}　{old_email.translate(MARKDOWN_TEXT)}'
            new_email = repair['new_email']
            group.append(paragraph + f'  \n{text["new_email"]}　{new_email.translate(MARKDOWN_TEXT)}')
        paragraphs.append('\n'.join('> ' + line for line in '\n\n'.join(group).split('\n')))
    return '\n\n'.join(paragraphs)


def notify_admin_of_duplicate_emails(apps, schema_editor, groups):
    db = schema_editor.connection.alias
    User = apps.get_model('users', 'User')
    Preference = apps.get_model('users', 'Preference')
    MessageContent = apps.get_model('notifications', 'MessageContent')
    SiteMessage = apps.get_model('notifications', 'SiteMessage')
    users = User._base_manager.using(db)
    admin_id = users.filter(username='admin').values_list('pk', flat=True).first()
    if admin_id is None:
        logger.warning('Duplicate emails were repaired, but username=admin does not exist to receive the notice.')
        return

    user_ids = list(groups)
    for repairs in groups.values():
        user_ids.extend(user_id for user_id, _ in repairs)
    accounts = users.only('name', 'username', 'email').in_bulk(user_ids)
    language = Preference._base_manager.using(db).filter(
        user_id=admin_id, category='lina', name='lang',
    ).values_list('value', flat=True).first() or settings.LANGUAGE_CODE
    language = 'zh' if language.lower().replace('_', '-').split('-')[0] == 'zh' else 'en'

    MessageContent._base_manager.using(db).get_or_create(
        pk=NOTICE_ID,
        defaults={
            'subject': NOTICE_TEXT[language]['subject'],
            'message': notification_body(groups, accounts, language),
            'display_mode': 'popup',
            'is_broadcast': False,
            'sender_id': None,
        },
    )
    SiteMessage._base_manager.using(db).get_or_create(
        pk=DELIVERY_ID,
        defaults={'content_id': NOTICE_ID, 'user_id': admin_id, 'has_read': False},
    )


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
    groups = defaultdict(list)
    for user_id, email, (keeper_id, keeper_email) in duplicates:
        candidate, lookup = replacement_address(email, user_id, occupied)
        occupied.add(lookup)
        users.filter(pk=user_id).update(email=candidate, email_lookup=lookup)
        groups[keeper_id].append((user_id, {
            'keeper_email': keeper_email,
            'old_email': email, 'new_email': candidate,
        }))
    for offset in range(0, len(lookup_updates), 1000):
        users.bulk_update(lookup_updates[offset:offset + 1000], ['email_lookup'], batch_size=1000)

    # Persist the repairs and their notice together before MySQL starts committing DDL.
    # After a DDL failure, both already exist and the next data pass finds no duplicates.
    if groups:
        notify_admin_of_duplicate_emails(apps, schema_editor, groups)

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
        ('notifications', '0003_messagecontent_display_mode'),
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

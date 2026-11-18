import json
import logging
import string
from collections import defaultdict
from uuid import NAMESPACE_URL, UUID, uuid5

from django.conf import settings
from django.db import migrations, transaction

from common.db.utils import Encryptor


logger = logging.getLogger(__name__)
NOTICE_ID = uuid5(NAMESPACE_URL, 'jumpserver:users:0010:duplicate-email-notice')
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
        'unknown': '未知',
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
        'unknown': 'Unknown',
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
        keeper = accounts.get(keeper_id)
        original = repairs[0][1].get('keeper_email') or (keeper.email if keeper else None)
        original = original or text['unknown']
        count = text['group_count'].format(count=len(repairs) + 1)
        group = [
            f'**{text["original_email"]}　{original.translate(MARKDOWN_TEXT)}（{count}）**',
            user_paragraph(text['kept'], keeper_id, accounts, text),
        ]
        for user_id, repair in repairs:
            paragraph = user_paragraph(text['changed'], user_id, accounts, text)
            old_email = repair.get('old_email')
            if old_email and old_email != original:
                paragraph += f'  \n{text["original_email"]}　{old_email.translate(MARKDOWN_TEXT)}'
            user = accounts.get(user_id)
            new_email = repair.get('new_email') or (user.email if user else None) or text['unknown']
            group.append(paragraph + f'  \n{text["new_email"]}　{new_email.translate(MARKDOWN_TEXT)}')
        paragraphs.append('\n'.join('> ' + line for line in '\n\n'.join(group).split('\n')))
    return '\n\n'.join(paragraphs)


def notify_admin_of_duplicate_emails(apps, schema_editor):
    db = schema_editor.connection.alias
    User = apps.get_model('users', 'User')
    Preference = apps.get_model('users', 'Preference')
    MessageContent = apps.get_model('notifications', 'MessageContent')
    SiteMessage = apps.get_model('notifications', 'SiteMessage')

    with transaction.atomic(using=db):
        markers = list(Preference._base_manager.using(db).filter(
            category='migration', name='users_0009_duplicate_email',
        ).order_by('pk').values_list('pk', 'user_id', 'encrypted', 'value'))
        if not markers:
            return
        users = User._base_manager.using(db)
        admin_id = users.filter(username='admin').values_list('pk', flat=True).first()
        if admin_id is None:
            logger.warning(
                'Duplicate email upgrade notice was not delivered: username=admin does not exist. '
                'Repair markers were preserved for review.'
            )
            return

        groups = defaultdict(list)
        user_ids = set()
        for _, user_id, encrypted, value in markers:
            # Earlier versions stored just the keeper's UUID.
            repair = json.loads(Encryptor(value).decrypt()) if encrypted else {'keeper_id': value}
            keeper_id = UUID(repair['keeper_id'])
            groups[keeper_id].append((user_id, repair))
            user_ids.update((keeper_id, user_id))
        accounts = users.only('name', 'username', 'email').in_bulk(user_ids)

        language = Preference._base_manager.using(db).filter(
            user_id=admin_id, category='lina', name='lang',
        ).values_list('value', flat=True).first() or settings.LANGUAGE_CODE
        language = 'zh' if language.lower().replace('_', '-').split('-')[0] == 'zh' else 'en'

        # Stable IDs make retries harmless and preserve an existing delivery's read state.
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
        Preference._base_manager.using(db).filter(pk__in=[marker[0] for marker in markers]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0009_enforce_user_email_uniqueness'),
        ('notifications', '0003_messagecontent_display_mode'),
    ]

    operations = [
        migrations.RunPython(notify_admin_of_duplicate_emails, migrations.RunPython.noop, atomic=True),
    ]

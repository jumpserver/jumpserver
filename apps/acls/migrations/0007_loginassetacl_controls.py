from django.db import migrations, models


LEGACY_CONTROLS = {
    'review': 'review_enabled',
    'notice': 'notice_enabled',
    'face_verify': 'face_verify_enabled',
    'face_online': 'face_online_enabled',
    'change_secret': 'change_secret_enabled',
}
NEW_CONTROLS = ('reason_enabled', 'mfa_enabled', 'push_account_enabled')


def move_users(ACL, database, rule_ids, source, destination):
    source_table = getattr(ACL, source).through
    destination_table = getattr(ACL, destination).through
    relations = source_table.objects.using(database).filter(loginassetacl_id__in=rule_ids)
    batch = []
    for rule_id, user_id in relations.values_list('loginassetacl_id', 'user_id').iterator(chunk_size=1000):
        batch.append(destination_table(loginassetacl_id=rule_id, user_id=user_id))
        if len(batch) == 1000:
            destination_table.objects.using(database).bulk_create(batch, ignore_conflicts=True, batch_size=1000)
            batch.clear()
    if batch:
        destination_table.objects.using(database).bulk_create(batch, ignore_conflicts=True, batch_size=1000)
    relations.delete()


def forwards(apps, schema_editor):
    ACL = apps.get_model('acls', 'LoginAssetACL')
    database = schema_editor.connection.alias
    rules = ACL.objects.using(database)
    if rules.exclude(action__in=('accept', 'reject', *LEGACY_CONTROLS)).exists():
        raise ValueError('Unknown asset login ACL action; migration aborted without changing policies.')
    move_users(ACL, database, rules.filter(action='notice').values('pk'), 'reviewers', 'recipients')
    for action, field in LEGACY_CONTROLS.items():
        rules.filter(action=action).update(action='accept', **{field: True})


def backwards(apps, schema_editor):
    ACL = apps.get_model('acls', 'LoginAssetACL')
    database = schema_editor.connection.alias
    rules = ACL.objects.using(database)
    # Validate every row before updating: old actions cannot represent combinations.
    if (rules.filter(notice_enabled=False, recipients__isnull=False).exists()
            or rules.filter(notice_enabled=True, reviewers__isnull=False).exists()):
        raise ValueError('Separate approval and notification recipients cannot be represented by the old schema.')
    fields = ('action', *LEGACY_CONTROLS.values(), *NEW_CONTROLS)
    for rule in rules.only(*fields).iterator(chunk_size=1000):
        controls = [action for action, field in LEGACY_CONTROLS.items() if getattr(rule, field)]
        if 'face_online' in controls and 'face_verify' in controls:
            controls.remove('face_verify')
        if (any(getattr(rule, field) for field in NEW_CONTROLS)
                or len(controls) > 1 or (rule.action == 'reject' and controls)):
            raise ValueError('Asset login ACL uses controls unsupported by the old schema; disable them before rollback.')
    move_users(ACL, database, rules.filter(notice_enabled=True).values('pk'), 'recipients', 'reviewers')
    for action, field in LEGACY_CONTROLS.items():
        queryset = rules.filter(**{field: True})
        if action == 'face_verify':
            queryset = queryset.filter(face_online_enabled=False)
        queryset.update(action=action)


class Migration(migrations.Migration):
    dependencies = [('acls', '0006_loginassetacl_review_duration')]

    operations = [
        migrations.AddField(model_name='loginassetacl', name=name, field=models.BooleanField(default=False, verbose_name=label))
        for name, label in (
            ('reason_enabled', 'Connection reason'), ('mfa_enabled', 'MFA verification'),
            ('review_enabled', 'Review'), ('notice_enabled', 'Notify'),
            ('face_verify_enabled', 'Face verify'), ('face_online_enabled', 'Face online'),
            ('push_account_enabled', 'Push account'), ('change_secret_enabled', 'Secret rotation'),
        )
    ] + [
        migrations.AddField(model_name='loginassetacl', name='recipients', field=models.ManyToManyField(blank=True, related_name='asset_acl_notifications', to='users.user', verbose_name='Recipients')),
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(model_name='loginassetacl', name='action', field=models.CharField(choices=[('accept', 'Accept'), ('reject', 'Reject')], default='reject', max_length=64, verbose_name='Action')),
    ]

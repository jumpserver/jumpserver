from django.db import migrations


def disable_empty_review_acls(apps, schema_editor):
    ACL = apps.get_model('acls', 'LoginAssetACL')
    # These rules were previously skipped in their entirety. Disabling them
    # preserves that effect while the runtime stops skipping malformed rules.
    ACL.objects.using(schema_editor.connection.alias).filter(
        action='accept', review_enabled=True, reviewers__isnull=True, is_active=True,
    ).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [('acls', '0007_loginassetacl_controls')]

    operations = [
        # Rollback must not reactivate a policy without an approval recipient.
        migrations.RunPython(disable_empty_review_acls, migrations.RunPython.noop),
    ]

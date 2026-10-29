from django.db import migrations
from django.db.models import OuterRef, Subquery


def backfill_calls(apps, schema_editor):
    db = schema_editor.connection.alias
    Log = apps.get_model('audits', 'IntegrationApplicationLog')
    Audit = apps.get_model('accounts', 'ApplicationAudit')
    Application = apps.get_model('accounts', 'IntegrationApplication')
    Account = apps.get_model('accounts', 'Account')
    applications = Application.objects.using(db)
    Log.objects.using(db).filter(org_id='', service_id__in=applications.values('id')).update(
        org_id=Subquery(applications.filter(id=OuterRef('service_id')).values('org_id')[:1]),
    )
    rows = Audit.objects.using(db).filter(event='credential_fetched', service_id__isnull=False).order_by('id')
    batch = []

    def copy_batch(audits):
        existing = set(Log.objects.using(db).filter(pk__in=[a.id for a in audits]).values_list('id', flat=True))
        accounts = {a['id']: a for a in Account.objects.using(db).filter(
            id__in=[a.account_id for a in audits if a.account_id],
        ).values('id', 'org_id', 'username', 'asset_id', 'asset__name', 'asset__address')}
        created, dates = [], {}
        for audit in audits:
            if audit.id in existing:
                continue
            account = accounts.get(audit.account_id)
            if account and str(account['org_id']) != str(audit.org_id):
                account = None
            account_name, asset_name, asset_id = audit.account, '', None
            if account:
                account_name = f"{audit.account}({account['username']})"[:128]
                asset_name = f"{account['asset__name']}({account['asset__address']})"[:128]
                asset_id = account['asset_id']
            created.append(Log(
                id=audit.id, org_id=audit.org_id, service=audit.service, service_id=audit.service_id,
                remote_addr=audit.remote_addr, account=account_name, account_id=audit.account_id,
                asset=asset_name, asset_id=asset_id, credential_id=audit.credential_id,
                credential_key=audit.credential_key, instance_id=audit.instance_id,
                source=audit.source, result=audit.result, revision=audit.revision, summary=audit.summary,
            ))
            dates[audit.id] = audit.date_created
        Log.objects.using(db).bulk_create(created)
        # The original datetime uses auto_now; restore historical times after insertion.
        for row in created:
            if dates[row.id] is not None:
                row.datetime = dates[row.id]
        Log.objects.using(db).bulk_update(created, ['datetime'])

    for audit in rows.iterator(chunk_size=1000):
        batch.append(audit)
        if len(batch) == 1000:
            copy_batch(batch)
            batch = []
    if batch:
        copy_batch(batch)


class Migration(migrations.Migration):
    dependencies = [
        ('audits', '0010_application_credential_call_records'),
        ('accounts', '0028_applicationcredential_verify_before_switch'),
    ]
    operations = [migrations.RunPython(backfill_calls, migrations.RunPython.noop)]

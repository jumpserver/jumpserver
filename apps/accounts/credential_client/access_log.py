"""One call record per credential response; keep the original audit table contract."""
from accounts.const import AuditSource
from audits.models import IntegrationApplicationLog


def record_access(*, application=None, client=None, account=None, credential=None, **values):
    if client:
        application = client.application
        values.setdefault('instance_id', client.instance_id)
        values.setdefault('source', AuditSource.AGENT if client.type == 'agent' else AuditSource.SDK)
    if application is None:
        raise ValueError('Credential call records require a trusted application')
    if account:
        asset = account.asset
        values.update(
            account=f'{account.name}({account.username})'[:128], account_id=account.id,
            asset=f'{asset.name}({asset.address})'[:128], asset_id=asset.id,
        )
    if credential:
        values.update(credential_id=credential.id, credential_key=credential.key)
    return IntegrationApplicationLog.objects.create(
        org_id=str(application.org_id), service=application.name, service_id=application.id,
        **values,
    )

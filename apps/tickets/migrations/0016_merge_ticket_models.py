from django.db import migrations


def migrate_payloads(apps, schema_editor):
    db = schema_editor.connection.alias
    Ticket = apps.get_model('tickets', 'Ticket')

    def copy(model_name, values):
        Model = apps.get_model('tickets', model_name)
        rows = Model.objects.using(db).all()
        if model_name == 'ApplyAssetTicket':
            rows = rows.prefetch_related('apply_assets', 'apply_nodes')
        pending = []
        for row in rows.iterator(chunk_size=500):
            payload = dict(row.request_data or {})
            payload.update(values(row))
            pending.append(Ticket(pk=row.pk, request_data=payload))
            if len(pending) == 500:
                Ticket.objects.using(db).bulk_update(pending, ['request_data'])
                pending.clear()
        if pending:
            Ticket.objects.using(db).bulk_update(pending, ['request_data'])

    copy('ApplyAssetTicket', lambda row: {
        'apply_permission_name': row.apply_permission_name,
        'apply_assets': [str(asset.pk) for asset in row.apply_assets.all()],
        'apply_nodes': [str(node.pk) for node in row.apply_nodes.all()],
        'apply_accounts': row.apply_accounts,
        'apply_actions': row.apply_actions,
        'apply_date_start': row.apply_date_start.isoformat() if row.apply_date_start else None,
        'apply_date_expired': row.apply_date_expired.isoformat() if row.apply_date_expired else None,
        'apply_expire_soon_notice_minutes': row.apply_expire_soon_notice_minutes,
    })
    copy('ApplyLoginTicket', lambda row: {
        'apply_login_ip': row.apply_login_ip,
        'apply_login_city': row.apply_login_city,
        'apply_login_datetime': row.apply_login_datetime.isoformat() if row.apply_login_datetime else None,
    })
    copy('ApplyLoginAssetTicket', lambda row: {
        'apply_login_user': str(row.apply_login_user_id) if row.apply_login_user_id else None,
        'apply_login_asset': str(row.apply_login_asset_id) if row.apply_login_asset_id else None,
        'apply_login_account': row.apply_login_account,
    })
    copy('ApplyCommandTicket', lambda row: {
        'apply_run_user': str(row.apply_run_user_id) if row.apply_run_user_id else None,
        'apply_run_asset': row.apply_run_asset,
        'apply_run_command': row.apply_run_command,
        'apply_run_account': row.apply_run_account,
        'apply_from_session': str(row.apply_from_session_id) if row.apply_from_session_id else None,
        'apply_from_cmd_filter_acl': str(row.apply_from_cmd_filter_acl_id) if row.apply_from_cmd_filter_acl_id else None,
    })


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0015_ticket_origin'),
        ('authentication', '0011_connection_token_ticket'),
    ]

    operations = [
        migrations.RunPython(migrate_payloads),
        migrations.DeleteModel(name='ApplyAssetTicket'),
        migrations.DeleteModel(name='ApplyLoginTicket'),
        migrations.DeleteModel(name='ApplyLoginAssetTicket'),
        migrations.DeleteModel(name='ApplyCommandTicket'),
    ]

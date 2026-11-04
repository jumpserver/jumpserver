import re

from django.utils.translation import gettext as _


INVENTORY_ASSET_ID = re.compile(
    r'__[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    r'(?=\(.*\)$|$)',
    re.IGNORECASE,
)


class ConnectivityReportMixin:
    def get_report_template(self):
        return 'assets/connectivity_report.html'

    def get_report_context(self):
        context = super().get_report_context()
        result = context['result'] or {}
        asset_details = result.get('asset_details', {})
        rows = []

        def add_row(target, status, label, error=''):
            target = str(target)
            asset = asset_details.get(target, {})
            match = INVENTORY_ASSET_ID.search(target)
            name = asset.get('asset_name') or INVENTORY_ASSET_ID.sub('', target, count=1)
            if asset.get('asset_name') and match:
                name += target[match.end():]
            rows.append({
                'target': name,
                'asset_id': asset.get('asset_id') or (match.group()[2:] if match else ''),
                'asset_address': asset.get('asset_address', ''),
                'status': status,
                'status_label': label,
                'error': error,
            })

        for target, error in result.get('fail_assets', []):
            add_row(target, 'failed', _('Failed'), error)
        for target in result.get('error_assets', []):
            add_row(target, 'unsupported', _('Unsupported'))
        for target in result.get('ok_assets', []):
            add_row(target, 'success', _('Success'))

        context['report_rows'] = rows
        context['has_errors'] = bool(result.get('fail_assets'))
        return context

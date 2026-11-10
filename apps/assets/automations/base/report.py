import re

from django.utils.translation import gettext as _


INVENTORY_UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
INVENTORY_ASSET_ID = re.compile(
    rf'__(?P<asset_id>{INVENTORY_UUID})(?:__account_{INVENTORY_UUID})?(?=\(.*\)$|$)',
    re.IGNORECASE,
)


class ConnectivityReportMixin:
    def get_report_template(self):
        return 'assets/connectivity_report.html'

    def get_report_failure_labels(self, result):
        return {}

    def get_report_context(self):
        context = super().get_report_context()
        result = context['result'] or {}
        asset_details = result.get('asset_details', {})
        failure_labels = self.get_report_failure_labels(result)
        rows = []

        def add_row(target, status, label, error='', target_label=''):
            target = str(target)
            asset = asset_details.get(target, {})
            match = INVENTORY_ASSET_ID.search(target)
            name = asset.get('asset_name') or INVENTORY_ASSET_ID.sub('', target, count=1)
            if asset.get('asset_name') and match:
                name += target[match.end():]
            rows.append({
                'target': target_label or name,
                'asset_id': asset.get('asset_id') or (match['asset_id'] if match else ''),
                'asset_address': asset.get('asset_address', ''),
                'status': status,
                'status_label': label,
                'error': error,
            })

        for target, error in result.get('fail_assets', []):
            add_row(target, 'failed', _('Failed'), error, failure_labels.get(str(target), ''))
        for target in result.get('error_assets', []):
            add_row(target, 'unsupported', _('Unsupported'))
        for target in result.get('ok_assets', []):
            add_row(target, 'success', _('Success'))

        context['report_rows'] = rows
        context['has_errors'] = bool(result.get('fail_assets'))
        return context

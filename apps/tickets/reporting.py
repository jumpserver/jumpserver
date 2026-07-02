from collections import Counter, OrderedDict, defaultdict

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.drf.reporting import BaseListReportExporter


class TicketReportExporter(BaseListReportExporter):
    report_title = _('Ticket Report')
    report_basename = 'ticket_report'

    def get_summary_sections(self):
        tickets = self.records
        overview = OrderedDict([
            (_('Total records'), len(tickets)),
            (_('Open tickets'), len([item for item in tickets if item.status == 'open'])),
            (_('Closed tickets'), len([item for item in tickets if item.status == 'closed'])),
            (_('Pending tickets'), len([item for item in tickets if item.state == 'pending'])),
            (_('Approved tickets'), len([item for item in tickets if item.state == 'approved'])),
            (_('Rejected tickets'), len([item for item in tickets if item.state == 'rejected'])),
            (_('Unique applicants'), len({
                item.applicant_id for item in tickets if getattr(item, 'applicant_id', None)
            })),
            (_('Unique organizations'), len({item.org_id for item in tickets if item.org_id})),
        ])

        created_trend = defaultdict(int)
        type_counter = Counter()
        state_counter = Counter()
        status_counter = Counter()
        org_counter = Counter()
        applicant_counter = Counter()
        approval_step_counter = Counter()

        for ticket in tickets:
            created_time = getattr(ticket, 'date_created', None)
            if created_time:
                report_date = timezone.localtime(created_time).strftime('%Y-%m-%d')
                created_trend[report_date] += 1

            type_counter[str(ticket.get_type_display())] += 1
            state_counter[str(ticket.get_state_display())] += 1
            status_counter[str(ticket.get_status_display())] += 1
            approval_step_counter[str(ticket.approval_step)] += 1

            org_name = getattr(ticket, 'org_name', None)
            if org_name:
                org_counter[str(org_name)] += 1

            applicant = getattr(ticket, 'applicant', None)
            if applicant:
                applicant_name = applicant.name or applicant.username
                applicant_counter[str(applicant_name)] += 1

        trend_rows = [
            [date, created_trend[date]]
            for date in sorted(created_trend.keys())
        ]

        return [
            self.build_key_value_section(_('Overview'), overview.items()),
            self.build_table_section(
                _('Created Trend'),
                [_('Date'), _('Count')],
                trend_rows,
            ),
            self.build_table_section(
                _('Ticket Type Distribution'),
                [_('Type'), _('Count')],
                self.build_counter_rows(type_counter),
            ),
            self.build_table_section(
                _('Ticket State Distribution'),
                [_('State'), _('Count')],
                self.build_counter_rows(state_counter),
            ),
            self.build_table_section(
                _('Ticket Status Distribution'),
                [_('Status'), _('Count')],
                self.build_counter_rows(status_counter),
            ),
            self.build_table_section(
                _('Organization Top 10'),
                [_('Organization'), _('Count')],
                self.build_counter_rows(org_counter, top_n=10),
            ),
            self.build_table_section(
                _('Applicant Top 10'),
                [_('Applicant'), _('Count')],
                self.build_counter_rows(applicant_counter, top_n=10),
            ),
            self.build_table_section(
                _('Approval Step Distribution'),
                [_('Approval step'), _('Count')],
                self.build_counter_rows(approval_step_counter),
            ),
        ]

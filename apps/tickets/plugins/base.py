from django.utils.module_loading import import_string


class TicketPlugin:
    type = ''
    label = ''
    visible = True
    self_service = False
    creation_modes = None
    allow_global = False
    global_options_permission = None
    execution_mode = 'approval_only'
    apply_serializer = None
    request_serializer = None

    def get_request_serializer(self, **kwargs):
        return import_string(self.request_serializer)(**kwargs)

    def build_context(self, ticket):
        """Return business context only; shared identity is set by the server."""
        return {'request': dict(ticket.request_data)}

    def validate_submission(self, ticket, context):
        """Check type-specific constraints before starting a workflow."""

    def filter_workflow_options(self, request, org_id, workflows):
        """Restrict workflows offered for this type and request."""
        return workflows

    def excluded_approver_ids(self, context, applicant_id):
        """Return approver IDs barred by this ticket type."""
        return set()

    def notify_processed(self, ticket, processor):
        """Send type-specific result notifications."""

    def allow_direct_approval(self, ticket):
        """Whether an approval notification may include a direct action link."""
        return True

    def on_approved(self, instance, ticket):
        """Optional synchronous, transactional effect. Return executed action data.

        None means approval only, not that an operation has been performed.
        Include resources (type, id, name) to snapshot resulting business objects.
        Remote work should use the business module's existing task mechanism.
        """
        return None

    def get_result_resources(self, instance, event, user):
        """Present action resources; override to add labels and authorized UI URLs.

        Names come from the execution snapshot. Resolve links at read time after
        checking the viewer's permission and the object's organization/existence.
        The default deliberately exposes no links, including persisted URLs.
        """
        return [{key: resource[key] for key in ('type', 'id', 'name') if key in resource}
                for resource in event.data.get('resources', [])]

    def get_available_actions(self, ticket, user):
        """Return only operations the current user may perform now."""
        return []

    def request_items(self, ticket):
        if not self.request_serializer:
            return []
        serializer = self.get_request_serializer()
        instance = getattr(ticket, 'workflow_instance', None)
        data = instance.context['request'] if instance else ticket.request_data
        items = []
        for name, field in serializer.fields.items():
            value = data.get(name)
            if value is None:
                continue
            if instance and field.style.get('resource') == 'asset':
                asset = next((asset for asset in instance.context.get('assets', []) if asset['id'] == value), None)
                if asset:
                    value = f"{asset['name']} ({asset['address']})"
            items.append({'name': name, 'label': str(field.label or name), 'value': value})
        return items

    def metadata(self):
        from .schema import request_fields
        return {
            'type': self.type, 'label': str(self.label), 'self_service': self.self_service,
            'creation_modes': list(self.creation_modes or (('manual',) if self.self_service else ('system',))),
            'execution_mode': self.execution_mode,
            'fields': request_fields(self.get_request_serializer()) if self.request_serializer else [],
        }

    def options(self, request, org_id):
        from rest_framework.exceptions import ValidationError
        from .resources import AssetAccountRequestSerializer
        if self.request_serializer:
            serializer = self.get_request_serializer(context={'request': request, 'org_id': org_id})
            if isinstance(serializer, AssetAccountRequestSerializer):
                return serializer.account_options(request.query_params.get('asset'))
        raise ValidationError('This ticket type has no resource options.')

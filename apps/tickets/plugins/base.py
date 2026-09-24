from django.utils.module_loading import import_string


class TicketPlugin:
    type = ''
    label = ''
    visible = True
    self_service = False
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

    def on_approved(self, instance, ticket):
        """Optional synchronous, transactional effect. Return executed action data.

        None means approval only, not that an operation has been performed.
        Remote work should use the business module's existing task mechanism.
        """
        return None

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
            'execution_mode': self.execution_mode,
            'fields': request_fields(self.get_request_serializer()) if self.request_serializer else [],
        }

    def options(self, request, org_id):
        from rest_framework.exceptions import ValidationError
        raise ValidationError('This ticket type has no resource options.')

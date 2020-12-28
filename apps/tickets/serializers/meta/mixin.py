from collections import OrderedDict


class TicketMetaSerializerMixin:
    need_fields_prefix = None

    def get_fields(self):
        fields = super().get_fields()
        if not self.need_fields_prefix:
            return fields
        need_fields = OrderedDict({
            field_name: field for field_name, field in fields.items()
            if field_name.startswith(self.need_fields_prefix)
        })
        return need_fields

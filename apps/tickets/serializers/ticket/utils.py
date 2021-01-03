from .meta import get_meta_field_mapping_rule_by_view

__all__ = [
    'get_dynamic_mapping_fields_mapping_rule_by_view'
]


#
# get `dynamic fields` mapping rule by `view object`
# ----------------------------------------------------


def get_dynamic_mapping_fields_mapping_rule_by_view(view):
    return {
        'meta': get_meta_field_mapping_rule_by_view(view=view)
    }

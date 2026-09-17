from rest_framework import filters


class AuthKeyQueryDeclaration(filters.BaseFilterBackend):
    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'authkey',
                'in': 'query',
                'required': True,
                'description': 'authkey',
                'schema': {'type': 'string', 'title': 'authkey'},
            }
        ]

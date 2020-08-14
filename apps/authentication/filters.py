from rest_framework import filters
from rest_framework.compat import coreapi, coreschema


class AuthKeyQueryDeclaration(filters.BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name='authkey', location='query', required=True, type='string',
                schema=coreschema.String(
                    title='authkey',
                    description='authkey'
                )
            )
        ]


__all__ = ['Endpoint', 'MethodSchema', 'QueryField', 'BodyField']


class Field:
    
    def __init__(self, name, field_type, required=False, description=''):
        self.name = name
        self.field_type = field_type
        self.required = required
        self.description = description


class QueryField(Field):
    pass


class BodyField(Field):

    def __init__(self, **kwargs):
        self.child = []
        super().__init__(**kwargs)
    
    def extend_child(self, child):
        self.child.extend(child)


class MethodSchema:
    
    def __init__(self, method, query_fields, body_fields):
        self.method = method
        self.query_fields = query_fields
        self.body_fields = body_fields


class Endpoint:

    def __init__(self, path, requires_auth=True):
        self.path = path
        self.methods = {}
        self.requires_auth = requires_auth

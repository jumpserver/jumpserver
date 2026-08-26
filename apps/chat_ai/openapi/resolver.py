from copy import deepcopy


class SchemaResolver:
    def __init__(self, document):
        self.document = document

    def resolve(self, value, seen=None):
        if seen is None:
            seen = set()
        if isinstance(value, list):
            return [self.resolve(item, seen.copy()) for item in value]
        if not isinstance(value, dict):
            return value

        ref = value.get('$ref')
        if ref:
            if ref in seen or not ref.startswith('#/'):
                return {'$ref': ref}
            target = self.document
            try:
                for part in ref[2:].split('/'):
                    target = target[part.replace('~1', '/').replace('~0', '~')]
            except (KeyError, TypeError):
                return deepcopy(value)
            merged = deepcopy(target)
            merged.update({key: item for key, item in value.items() if key != '$ref'})
            seen.add(ref)
            return self.resolve(merged, seen)

        return {key: self.resolve(item, seen.copy()) for key, item in value.items()}


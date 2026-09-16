import json


class AbstractModel:
    _fields = {}
    _required = ()

    def __init__(self, **kwargs):
        unknown = set(kwargs) - set(self._fields)
        if unknown:
            raise TypeError(f'Unknown fields: {", ".join(sorted(unknown))}')
        for name in self._fields:
            setattr(self, name, kwargs.get(name))

    @staticmethod
    def _serialize_value(value):
        if isinstance(value, AbstractModel):
            return value._serialize()
        if isinstance(value, list):
            return [AbstractModel._serialize_value(item) for item in value]
        return value

    def _serialize(self):
        return {
            wire_name: self._serialize_value(getattr(self, name))
            for name, (wire_name, _) in self._fields.items()
            if getattr(self, name) is not None
        }

    def _deserialize(self, params):
        if not isinstance(params, dict):
            raise TypeError('Response body must be a JSON object')
        for name, (wire_name, model_type) in self._fields.items():
            if wire_name not in params:
                continue
            value = params[wire_name]
            if model_type and value is not None:
                if isinstance(model_type, list):
                    value = [model_type[0]()._deserialize(item) for item in value]
                else:
                    value = model_type()._deserialize(value)
            setattr(self, name, value)
        return self

    def _validate(self):
        missing = [name for name in self._required if getattr(self, name) in (None, '')]
        if missing:
            raise ValueError(f'{", ".join(missing)} is required')
        for name, (_, model_type) in self._fields.items():
            value = getattr(self, name)
            if not model_type or value is None:
                continue
            if isinstance(model_type, list):
                if not isinstance(value, list) or not all(
                    isinstance(item, model_type[0]) for item in value
                ):
                    raise TypeError(f'{name} contains an invalid model')
                for item in value:
                    item._validate()
            elif not isinstance(value, model_type):
                raise TypeError(f'{name} contains an invalid model')
            else:
                value._validate()
        return self

    def to_json_string(self):
        return json.dumps(self._serialize(), ensure_ascii=False)

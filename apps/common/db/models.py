from functools import partial


class Choice(str):
    def __new__(cls, value, label):
        self = super().__new__(cls, value)
        self.label = label
        return self


class ChoiceSetType(type):
    def __new__(cls, name, bases, attrs):
        _choices = []
        collected = set()
        new_attrs = {}
        for k, v in attrs.items():
            if isinstance(v, tuple):
                v = Choice(*v)
                assert v not in collected, 'Cannot be defined repeatedly'
                _choices.append(v)
                collected.add(v)
            new_attrs[k] = v
        for base in bases:
            if hasattr(base, '_choices'):
                for c in base._choices:
                    if c not in collected:
                        _choices.append(c)
                        collected.add(c)
        new_attrs['_choices'] = _choices
        new_attrs['_choices_dict'] = {c: c.label for c in _choices}
        return type.__new__(cls, name, bases, new_attrs)

    def __contains__(self, item):
        return self._choices_dict.__contains__(item)

    def __getitem__(self, item):
        return self._choices_dict.__getitem__(item)

    def get(self, item, default=None):
        return self._choices_dict.get(item, default=None)

    @property
    def choices(self):
        return [(c, c.label) for c in self._choices]


class ChoiceSet(metaclass=ChoiceSetType):
    choices = None  # 用于 Django Model 中的 choices 配置， 为了代码提示在此声明

# -*- coding: utf-8 -*-
#

import ipaddress
import json
import logging
import re

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q, Manager, QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework.utils.encoders import JSONEncoder

from common.local import add_encrypted_field_set
from common.utils import contains_ip
from .utils import Encryptor
from .validators import PortRangeValidator

__all__ = [
    "JsonMixin",
    "JsonDictMixin",
    "JsonListMixin",
    "JsonTypeMixin",
    "JsonCharField",
    "JsonTextField",
    "JsonListCharField",
    "JsonListTextField",
    "JsonDictCharField",
    "JsonDictTextField",
    "EncryptCharField",
    "EncryptTextField",
    "EncryptMixin",
    "EncryptJsonDictTextField",
    "EncryptJsonDictCharField",
    "PortField",
    "PortRangeField",
    "BitChoices",
    "TreeChoices",
    "JSONManyToManyField",
]


class JsonMixin:
    tp = None

    @staticmethod
    def json_decode(data):
        try:
            return json.loads(data)
        except (TypeError, json.JSONDecodeError):
            return None

    @staticmethod
    def json_encode(data):
        return json.dumps(data, cls=JSONEncoder)

    def from_db_value(self, value, expression, connection, context=None):
        if value is None:
            return value
        return self.json_decode(value)

    def to_python(self, value):
        if value is None:
            return value

        if not isinstance(value, str) or not value.startswith('"'):
            return value
        else:
            return self.json_decode(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return self.json_encode(value)


class JsonTypeMixin(JsonMixin):
    tp = dict

    def from_db_value(self, value, expression, connection, context=None):
        value = super().from_db_value(value, expression, connection, context)
        if not isinstance(value, self.tp):
            value = self.tp()
        return value

    def to_python(self, value):
        data = super().to_python(value)
        if not isinstance(data, self.tp):
            data = self.tp()
        return data

    def get_prep_value(self, value):
        if not isinstance(value, self.tp):
            value = self.tp()
        return self.json_encode(value)


class JsonDictMixin(JsonTypeMixin):
    tp = dict


class JsonDictCharField(JsonDictMixin, models.CharField):
    description = _("Marshal dict data to char field")


class JsonDictTextField(JsonDictMixin, models.TextField):
    description = _("Marshal dict data to text field")


class JsonListMixin(JsonTypeMixin):
    tp = list


class JsonStrListMixin(JsonListMixin):
    pass


class JsonListCharField(JsonListMixin, models.CharField):
    description = _("Marshal list data to char field")


class JsonListTextField(JsonListMixin, models.TextField):
    description = _("Marshal list data to text field")


class JsonCharField(JsonMixin, models.CharField):
    description = _("Marshal data to char field")


class JsonTextField(JsonMixin, models.TextField):
    description = _("Marshal data to text field")


class EncryptMixin:
    """
    EncryptMixin要放在最前面
    """

    def from_db_value(self, value, expression, connection, context=None):
        if value is None:
            return value

        plain_value = Encryptor(value).decrypt()
        # 可能和Json mix，所以要先解密，再json
        sp = super()
        if hasattr(sp, "from_db_value"):
            plain_value = sp.from_db_value(plain_value, expression, connection, context)
        return plain_value

    def get_prep_value(self, value):
        if value is None:
            return value

        # 先 json 再解密
        sp = super()
        if hasattr(sp, "get_prep_value"):
            value = sp.get_prep_value(value)

        # 替换新的加密方式
        return Encryptor(value).encrypt()


class EncryptTextField(EncryptMixin, models.TextField):
    description = _("Encrypt field using Secret Key")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_encrypted_field_set(self.verbose_name)


class EncryptCharField(EncryptMixin, models.CharField):
    @staticmethod
    def change_max_length(kwargs):
        kwargs.setdefault("max_length", 1024)
        max_length = kwargs.get("max_length")
        if max_length < 129:
            max_length = 128
        max_length = max_length * 2
        kwargs["max_length"] = max_length

    def __init__(self, *args, **kwargs):
        self.change_max_length(kwargs)
        super().__init__(*args, **kwargs)
        add_encrypted_field_set(self.verbose_name)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        max_length = kwargs.pop("max_length")
        if max_length > 255:
            max_length = max_length // 2
        kwargs["max_length"] = max_length
        return name, path, args, kwargs


class EncryptJsonDictTextField(EncryptMixin, JsonDictTextField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_encrypted_field_set(self.verbose_name)


class EncryptJsonDictCharField(EncryptMixin, JsonDictCharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_encrypted_field_set(self.verbose_name)


class PortField(models.IntegerField):
    def __init__(self, *args, **kwargs):
        kwargs.update(
            {
                "blank": False,
                "null": False,
                "validators": [MinValueValidator(0), MaxValueValidator(65535)],
            }
        )
        super().__init__(*args, **kwargs)


class TreeChoices(models.Choices):
    @classmethod
    def is_tree(cls):
        return True

    @classmethod
    def branches(cls):
        return [i for i in cls]

    @classmethod
    def tree(cls):
        if not cls.is_tree():
            return []
        root = [_("All"), cls.branches()]
        return [cls.render_node(root)]

    @classmethod
    def render_node(cls, node):
        if isinstance(node, models.Choices):
            return {
                "value": node.name,
                "label": node.label,
            }
        else:
            name, children = node
            return {
                "value": name,
                "label": name,
                "children": [cls.render_node(child) for child in children],
            }

    @classmethod
    def all(cls):
        return [i[0] for i in cls.choices]


class BitChoices(models.IntegerChoices, TreeChoices):
    @classmethod
    def is_tree(cls):
        return False

    @classmethod
    def all(cls):
        # 权限 12 位 最大值
        return 4095


class PortRangeField(models.CharField):
    def __init__(self, **kwargs):
        kwargs['max_length'] = 16
        super().__init__(**kwargs)
        self.validators.append(PortRangeValidator())


class RelatedManager:
    def __init__(self, instance, field):
        self.instance = instance
        self.field = field
        self.value = None

    def set(self, value):
        self.value = value
        self.instance.__dict__[self.field.name] = value

    @classmethod
    def get_to_filter_qs(cls, value, to_model):
        """
        这个是 instance 去查找 to_model 的 queryset 的 Q
        :param value:
        :param to_model:
        :return:
        """
        default = [Q()]
        if not value or not isinstance(value, dict):
            return default

        if value["type"] == "all":
            return default
        elif value["type"] == "ids" and isinstance(value.get("ids"), list):
            return [Q(id__in=value["ids"])]
        elif value["type"] == "attrs" and isinstance(value.get("attrs"), list):
            return cls._get_filter_attrs_qs(value, to_model)
        else:
            return default

    @classmethod
    def filter_queryset_by_model(cls, value, to_model):
        if hasattr(to_model, "get_queryset"):
            queryset = to_model.get_queryset()
        else:
            queryset = to_model.objects.all()
        qs = cls.get_to_filter_qs(value, to_model)
        for q in qs:
            queryset = queryset.filter(q)
        return queryset.distinct()

    @staticmethod
    def get_ip_in_q(name, val):
        q = Q()
        if isinstance(val, str):
            val = [val]
        if ['*'] in val:
            return Q()
        for ip in val:
            if not ip:
                continue
            try:
                if '/' in ip:
                    network = ipaddress.ip_network(ip)
                    ips = network.hosts()
                    q |= Q(**{"{}__in".format(name): ips})
                elif '-' in ip:
                    start_ip, end_ip = ip.split('-')
                    start_ip = ipaddress.ip_address(start_ip)
                    end_ip = ipaddress.ip_address(end_ip)
                    q |= Q(**{"{}__range".format(name): (start_ip, end_ip)})
                elif len(ip.split('.')) == 4:
                    q |= Q(**{"{}__exact".format(name): ip})
                else:
                    q |= Q(**{"{}__startswith".format(name): ip})
            except ValueError:
                continue
        return q

    @classmethod
    def _get_filter_attrs_qs(cls, value, to_model):
        filters = []
        # 特殊情况有这几种，
        # 1. 像 资产中的 type 和 category，集成自 Platform。所以不能直接查询
        # 2. 像 资产中的 nodes，不是简单的 m2m，是树 的关系
        # 3. 像 用户中的 orgs 也不是简单的 m2m，也是计算出来的
        # get_filter_{}_attr_q 处理复杂的
        custom_attr_filter = getattr(to_model, "get_json_filter_attr_q", None)
        for attr in value["attrs"]:
            if not isinstance(attr, dict):
                continue

            name = attr.get('name')
            val = attr.get('value')
            match = attr.get('match', 'exact')
            if name is None or val is None:
                continue

            custom_filter_q = None
            spec_attr_filter = getattr(to_model, "get_{}_filter_attr_q".format(name), None)
            if spec_attr_filter:
                custom_filter_q = spec_attr_filter(val, match)
            elif custom_attr_filter:
                custom_filter_q = custom_attr_filter(name, val, match)
            if custom_filter_q:
                filters.append(custom_filter_q)
                continue

            if match == 'ip_in':
                q = cls.get_ip_in_q(name, val)
            elif match in ("contains", "startswith", "endswith", "gte", "lte", "gt", "lt"):
                lookup = "{}__{}".format(name, match)
                q = Q(**{lookup: val})
            elif match == 'regex':
                try:
                    re.compile(val)
                    lookup = "{}__{}".format(name, match)
                    q = Q(**{lookup: val})
                except re.error:
                    q = Q(pk__isnull=True)
            elif match == "not":
                q = ~Q(**{name: val})
            elif match.startswith('m2m'):
                if not isinstance(val, list):
                    val = [val]
                if match == 'm2m_all':
                    for v in val:
                        filters.append(Q(**{"{}__in".format(name): [v]}))
                    continue
                else:
                    q = Q(**{"{}__in".format(name): val})
            elif match == 'in':
                if not isinstance(val, list):
                    val = [val]
                q = Q() if '*' in val else Q(**{"{}__in".format(name): val})
            else:
                q = Q() if val == '*' else Q(**{name: val})
            filters.append(q)
        return filters

    def _get_queryset(self):
        to_model = apps.get_model(self.field.to)
        value = self.value
        return self.filter_queryset_by_model(value, to_model)

    def get_attr_q(self):
        to_model = apps.get_model(self.field.to)
        qs = self._get_filter_attrs_qs(self.value, to_model)
        return qs

    def all(self):
        return self._get_queryset()

    def filter(self, *args, **kwargs):
        queryset = self._get_queryset()
        return queryset.filter(*args, **kwargs)


class JSONManyToManyDescriptor:
    def __init__(self, field):
        self.field = field
        self._is_setting = False

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        if not hasattr(instance, "_related_manager_cache"):
            instance._related_manager_cache = {}
        if self.field.name not in instance._related_manager_cache:
            manager = RelatedManager(instance, self.field)
            instance._related_manager_cache[self.field.name] = manager
        manager = instance._related_manager_cache[self.field.name]
        return manager

    def __set__(self, instance, value):
        if instance is None:
            return

        if not hasattr(instance, "_related_manager_cache"):
            instance._related_manager_cache = {}

        if self.field.name not in instance._related_manager_cache:
            manager = self.__get__(instance, instance.__class__)
        else:
            manager = instance._related_manager_cache[self.field.name]

        if isinstance(value, RelatedManager):
            value = value.value
        manager.set(value)

    def is_match(self, obj, attr_rules):
        # m2m 的情况
        # 自定义的情况：比如 nodes, category
        res = True
        to_model = apps.get_model(self.field.to)
        custom_attr_filter = getattr(to_model, "get_json_filter_attr_q", None)

        custom_q = Q()
        for rule in attr_rules:
            value = getattr(obj, rule['name'], None) or ''
            rule_value = rule.get('value', '')
            rule_match = rule.get('match', 'exact')

            custom_filter_q = None
            spec_attr_filter = getattr(to_model, "get_filter_{}_attr_q".format(rule['name']), None)
            if spec_attr_filter:
                custom_filter_q = spec_attr_filter(rule_value, rule_match)
            elif custom_attr_filter:
                custom_filter_q = custom_attr_filter(rule['name'], rule_value, rule_match)
            if custom_filter_q:
                custom_q &= custom_filter_q
                continue

            if rule_match == 'in':
                res &= value in rule_value or '*' in rule_value
            elif rule_match == 'exact':
                res &= value == rule_value or rule_value == '*'
            elif rule_match == 'contains':
                res &= (rule_value in value)
            elif rule_match == 'startswith':
                res &= str(value).startswith(str(rule_value))
            elif rule_match == 'endswith':
                res &= str(value).endswith(str(rule_value))
            elif rule_match == 'regex':
                try:
                    matched = bool(re.search(r'{}'.format(rule_value), value))
                except Exception as e:
                    logging.error('Error regex match: %s', e)
                    matched = False
                res &= matched
            elif rule_match == 'not':
                res &= value != rule_value
            elif rule['match'] == 'gte':
                res &= value >= rule_value
            elif rule['match'] == 'lte':
                res &= value <= rule_value
            elif rule['match'] == 'gt':
                res &= value > rule_value
            elif rule['match'] == 'lt':
                res &= value < rule_value
            elif rule['match'] == 'ip_in':
                if isinstance(rule_value, str):
                    rule_value = [rule_value]
                res &= '*' in rule_value or contains_ip(value, rule_value)
            elif rule['match'].startswith('m2m'):
                if isinstance(value, Manager):
                    value = value.values_list('id', flat=True)
                elif isinstance(value, QuerySet):
                    value = value.values_list('id', flat=True)
                elif isinstance(value, models.Model):
                    value = [value.id]
                if isinstance(rule_value, (str, int)):
                    rule_value = [rule_value]
                value = set(map(str, value))
                rule_value = set(map(str, rule_value))

                if rule['match'] == 'm2m_all':
                    res &= rule_value.issubset(value)
                else:
                    res &= bool(value & rule_value)
            else:
                logging.error("unknown match: {}".format(rule['match']))
                res &= False

            if not res:
                return res
        if custom_q:
            res &= to_model.objects.filter(custom_q).filter(id=obj.id).exists()
        return res

    def get_filter_q(self, instance):
        """
        这个是某个 instance 获取 关联 资源的 filter q
        :param instance:
        :return:
        """
        model_cls = self.field.model
        field_name = self.field.column
        q = Q(**{f'{field_name}__type': 'all'}) | \
            Q(**{
                f'{field_name}__type': 'ids',
                f'{field_name}__ids__contains': [str(instance.id)]
            })
        queryset_id_attrs = model_cls.objects \
            .filter(**{'{}__type'.format(field_name): 'attrs'}) \
            .values_list('id', '{}__attrs'.format(field_name))
        ids = [str(_id) for _id, attr_rules in queryset_id_attrs
               if self.is_match(instance, attr_rules)]
        if ids:
            q |= Q(id__in=ids)
        return q


class JSONManyToManyField(models.JSONField):
    def __init__(self, to, *args, **kwargs):
        self.to = to
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.name, JSONManyToManyDescriptor(self))

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['to'] = self.to
        return name, path, args, kwargs

    @staticmethod
    def check_value(val):
        if not val:
            return val
        e = ValueError(_(
            "Invalid JSON data for JSONManyToManyField, should be like "
            "{'type': 'all'} or {'type': 'ids', 'ids': []} "
            "or {'type': 'attrs', 'attrs': [{'name': 'ip', 'match': 'exact', 'value': '1.1.1.1'}}"
        ))
        if not isinstance(val, dict):
            raise e
        if val["type"] not in ["all", "ids", "attrs"]:
            raise ValueError(_('Invalid type, should be "all", "ids" or "attrs"'))
        if val["type"] == "ids":
            if not isinstance(val["ids"], list):
                raise ValueError(_("Invalid ids for ids, should be a list"))
            if not val["ids"]:
                raise ValueError(_("This field is required."))
        elif val["type"] == "attrs":
            if not isinstance(val["attrs"], list):
                raise ValueError(_("Invalid attrs, should be a list of dict"))
            if not val["attrs"]:
                raise ValueError(_("This field is required."))
            for attr in val["attrs"]:
                if not isinstance(attr, dict):
                    raise ValueError(_("Invalid attrs, should be a list of dict"))
                if 'name' not in attr or 'value' not in attr:
                    raise ValueError(_("Invalid attrs, should be has name and value"))

    def get_prep_value(self, value):
        if value is None:
            return None
        if isinstance(value, RelatedManager):
            value = value.value
        return json.dumps(value)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if not isinstance(value, dict):
            raise ValidationError("Invalid JSON data for JSONManyToManyField.")
        self.check_value(value)

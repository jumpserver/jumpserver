import copy
from datetime import datetime
from itertools import chain

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import F, Value, CharField
from django.db.models.functions import Concat
from django.utils import translation
from django.utils.translation import gettext_noop

from rest_framework.exceptions import ValidationError
from rest_framework.fields import DateTimeField

from common.db.fields import RelatedManager
from common.utils import validate_ip, get_ip_city, get_logger, i18n_fmt
from common.utils.timezone import as_current_tz
from .const import ActionChoices, DEFAULT_CITY, ActivityChoices as LogChoice
from .handler import create_or_update_operate_log
from .models import ActivityLog

logger = get_logger(__name__)


def write_login_log(*args, **kwargs):
    from audits.models import UserLoginLog

    ip = kwargs.get('ip') or ''
    if not (ip and validate_ip(ip)):
        ip = ip[:15]
        city = DEFAULT_CITY
    else:
        city = get_ip_city(ip) or DEFAULT_CITY
    kwargs.update({'ip': ip, 'city': city})
    return UserLoginLog.objects.create(**kwargs)


def _get_instance_field_value(
        instance, include_model_fields,
        model_need_continue_fields, exclude_fields=None
):
    data = {}
    opts = getattr(instance, '_meta', None)
    if opts is not None:
        for f in chain(opts.concrete_fields, opts.private_fields):
            if not include_model_fields and not getattr(f, 'primary_key', False):
                continue

            if isinstance(f, GenericForeignKey):
                continue

            if isinstance(f, (models.FileField, models.ImageField)):
                continue

            if getattr(f, 'attname', None) in model_need_continue_fields:
                continue

            try:
                value = getattr(instance, f.name, None) or getattr(instance, f.attname, None)
            except ObjectDoesNotExist:
                continue
            if not isinstance(value, (bool, int)) and not value:
                continue

            choices = getattr(f, 'choices', []) or []
            for c_value, c_label in choices:
                if c_value == value:
                    value = c_label
                    break

            if getattr(f, 'primary_key', False):
                f.verbose_name = 'id'
            elif isinstance(value, list):
                value = copy.deepcopy(value)
            elif isinstance(value, dict):
                value = dict(copy.deepcopy(value))
            elif isinstance(value, datetime):
                value = as_current_tz(value).strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, RelatedManager):
                value = value.value
            elif isinstance(f, models.OneToOneField) and isinstance(value, models.Model):
                nested_data = _get_instance_field_value(
                    value, include_model_fields, model_need_continue_fields, ('id',)
                )
                for k, v in nested_data.items():
                    if exclude_fields and k in exclude_fields:
                        continue
                    data.setdefault(k, v)
                continue
            elif isinstance(f, GenericRelation):
                value = [str(v) for v in value.all()]
            elif isinstance(f, GenericForeignKey):
                continue
            try:
                data.setdefault(
                    str(f.verbose_name), {'name': getattr(f, 'column', ''), 'value': value}
                )
            except Exception as e:
                print(f.__dict__)
                raise e
    return data


def model_to_dict_for_operate_log(
        instance, include_model_fields=True, include_related_fields=None
):
    def get_related_values(f):
        value = []
        if instance.pk is not None:
            related_name = getattr(f, 'attname', '') or getattr(f, 'related_name', '')
            if not related_name or related_name in ['history_passwords']:
                return
            try:
                value = [str(i) for i in getattr(instance, related_name).all()]
            except:
                pass
        if not value:
            return
        try:
            field_key = getattr(f, 'verbose_name', None) or f.related_model._meta.verbose_name
            data.setdefault(
                str(field_key), {'name': getattr(f, 'column', ''), 'value': value}
            )
        except:
            pass

    data = _get_instance_field_value(
        instance, include_model_fields, ['date_updated']
    )

    if include_related_fields:
        opts = instance._meta
        for f in chain(opts.many_to_many, opts.related_objects):
            related_model = getattr(f, 'related_model', None)
            if related_model not in include_related_fields:
                continue
            get_related_values(f)

    return data


def construct_userlogin_usernames(user_queryset):
    usernames_original = user_queryset.values_list('username', flat=True)
    usernames_combined = user_queryset.annotate(
        usernames_combined_field=Concat(F('name'), Value('('), F('username'), Value(')'), output_field=CharField())
    ).values_list("usernames_combined_field", flat=True)
    usernames = list(chain(usernames_original, usernames_combined))
    return usernames


def _format_view_log_datetime(value):
    if not value:
        return None
    try:
        value = DateTimeField().to_internal_value(value)
    except (TypeError, ValueError, ValidationError):
        return None
    return as_current_tz(value).strftime('%Y-%m-%d %H:%M')


def _build_view_log_resource_display(resource_type, query_params, count):
    date_from = _format_view_log_datetime(query_params.get('date_from'))
    date_to = _format_view_log_datetime(query_params.get('date_to'))
    count_label = gettext_noop('Resource count')

    if date_from and date_to:
        return i18n_fmt(
            '%s: %s ~ %s, %s: %s', resource_type, date_from, date_to,
            count_label, count
        )
    if date_from:
        return i18n_fmt(
            '%s: %s: %s, %s: %s', resource_type,
            gettext_noop('Date from'), date_from, count_label, count
        )
    if date_to:
        return i18n_fmt(
            '%s: %s: %s, %s: %s', resource_type,
            gettext_noop('Date to'), date_to, count_label, count
        )
    return i18n_fmt(
        '%s: %s, %s: %s', resource_type, gettext_noop('All'),
        count_label, count
    )


def record_view_log(
        request, response, model, resource=None, resource_display=None,
        resource_type=None, exclude_params=()
):
    if request.method != 'GET':
        return
    if not 200 <= response.status_code < 300:
        return
    if request.query_params.get('format') in ('csv', 'xlsx'):
        return

    data = getattr(response, 'data', None)
    if isinstance(data, dict) and 'results' in data:
        data = data['results']
    elif isinstance(data, dict):
        data = [data]
    if not isinstance(data, (list, tuple)) or not data:
        return

    ignore_params = {
        'format', 'order', 'export_mode', 'refresh', '_', *exclude_params
    }
    params = {}
    for key, values in request.query_params.lists():
        if key in ignore_params:
            continue
        values = list(filter(None, values))
        if not values:
            continue
        value = values[0] if len(values) == 1 else values
        params[key] = {'value': value}
    params['Resource count'] = {'value': len(data)}

    with translation.override('en'):
        resource_type = resource_type or getattr(
            model._meta, 'verbose_name_raw', model._meta.verbose_name
        )
        if resource_display is None and resource is None:
            resource_display = _build_view_log_resource_display(
                resource_type, request.query_params, len(data)
            )
        create_or_update_operate_log(
            ActionChoices.view, resource_type, resource=resource,
            resource_display=resource_display, force=True, after=params
        )


def record_operate_log_and_activity_log(ids, action, detail, model, **kwargs):
    from orgs.utils import current_org

    org_id = current_org.id
    with translation.override('en'):
        resource_type = kwargs.pop('resource_type', None) or model._meta.verbose_name
        create_or_update_operate_log(action, resource_type, force=True, **kwargs)
        base_data = {'type': LogChoice.operate_log, 'detail': detail, 'org_id': org_id}
        activities = [ActivityLog(resource_id=r_id, **base_data) for r_id in ids]
        ActivityLog.objects.bulk_create(activities)

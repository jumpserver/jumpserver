from django.utils.translation import ugettext_lazy as _


ALLOW_APPS = ['accounts', 'namespaces', 'rbac']

ACTION_NAME = {
    'view': _('Can view %s'),
    'add': _('Can add %s'),
    'change': _('Can change %s'),
    'delete': _('Can delete %s'),
}


def get_permission_name(p):
    action = p.codename.split('_')[0]
    if action in ACTION_NAME:
        return ACTION_NAME[action] % str(p.content_type)
    else:
        return str(_(p.name))


def group_permissions(queryset):
    result = {}
    for obj in queryset:
        app_label = obj.content_type.app_label
        app = obj._meta.apps.app_configs.get(app_label)
        app_label_display = str(app.verbose_name) if app else app_label
        model_display = obj.content_type.name
        if app_label in ALLOW_APPS:
            permission_name = get_permission_name(obj)
            if app_label_display not in result:
                result[app_label_display] = {model_display: {obj.codename: {'id': obj.id, 'name': permission_name}}}
            else:
                if model_display not in result[app_label_display]:
                    result[app_label_display].update(
                        {model_display: {obj.codename: {'id': obj.id, 'name': permission_name}}})
                else:
                    result[app_label_display][model_display].update(
                        {obj.codename: {'id': obj.id, 'name': permission_name}})
    return result


def group_content_types(queryset):
    result = {}
    for obj in queryset:
        app = obj._meta.apps.app_configs.get(obj.app_label)
        app_label_display = str(app.verbose_name) if app else obj.app_label
        model_display = obj.name
        if obj.app_label in ALLOW_APPS:
            if app_label_display not in result:
                result[app_label_display] = {model_display: {'id': obj.id}}
            else:
                result[app_label_display].update({model_display: {'id': obj.id}})
    return result


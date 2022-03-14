import os
import sys
import django


if os.path.exists('../apps'):
    sys.path.insert(0, '../apps')
elif os.path.exists('./apps'):
    sys.path.insert(0, './apps')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

from rbac.models import Permission, ContentType


def clean_db_content_types():
    content_type_delete_required = [
        ('common', 'permission'),
    ]
    for app, model in content_type_delete_required:
        ContentType.objects.filter(app_label=app, model=model).delete()

    permissions_delete_required = [
        ('perms', 'assetpermission', 'connect_myassets'),
        ('perms', 'assetpermission', 'view_myassets'),
        ('perms', 'assetpermission', 'view_userassets'),
        ('perms', 'assetpermission', 'view_usergroupassets'),
        ('perms', 'applicationpermission', 'view_myapps'),
        ('perms', 'applicationpermission', 'connect_myapps'),
        ('perms', 'applicationpermission', 'view_userapps'),
        ('perms', 'applicationpermission', 'view_usergroupapps'),


        ('perms', 'permeddatabaseapp', 'connect_mydatabaseapp'),
        ('perms', 'permeddatabaseapp', 'view_mydatabaseapp'),
        ('perms', 'permedkubernetesapp', 'connect_mykubernetesapp'),
        ('perms', 'permedkubernetesapp', 'view_mykubernetesapp'),
        ('perms', 'permedremoteapp', 'connect_myremoteapp'),
        ('perms', 'permedremoteapp', 'view_myremoteapp'),

        ('applications', 'databaseapp', 'add_databaseapp'),
        ('applications', 'databaseapp', 'change_databaseapp'),
        ('applications', 'databaseapp', 'delete_databaseapp'),
        ('applications', 'databaseapp', 'view_databaseapp'),
        ('applications', 'k8sapp', 'add_k8sapp'),
        ('applications', 'k8sapp', 'change_k8sapp'),
        ('applications', 'k8sapp', 'delete_k8sapp'),
        ('applications', 'k8sapp', 'view_k8sapp'),
        ('applications', 'kubernetesapp', 'add_kubernetesapp'),
        ('applications', 'kubernetesapp', 'delete_kubernetesapp'),
        ('applications', 'kubernetesapp', 'change_kubernetesapp'),
        ('applications', 'kubernetesapp', 'view_kubernetesapp'),
        ('applications', 'remoteapp', 'add_remoteapp'),
        ('applications', 'remoteapp', 'change_remoteapp'),
        ('applications', 'remoteapp', 'delete_remoteapp'),
        ('applications', 'remoteapp', 'view_remoteapp'),

        ('settings', 'setting', 'change_terminal_basic_setting'),
        ('settings', 'setting', 'change_sys_msg_sub'),
        ('settings', 'setting', 'change_basic'),
        ('rbac', 'menupermission', 'view_userview'),
        ('rbac', 'menupermission', 'view_adminview'),
        ('rbac', 'menupermission', 'view_auditview'),
    ]
    for app, model, codename in permissions_delete_required:
        print('delete {}.{} ({})'.format(app, codename, model))
        Permission.objects.filter(
            codename=codename, content_type__model=model, content_type__app_label=app
        ).delete()


if __name__ == '__main__':
    clean_db_content_types()

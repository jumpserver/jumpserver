from django.db.models import TextChoices


class SuMethodChoices(TextChoices):
    sudo = "sudo", "sudo su -"
    su = "su", "su - "
    only_sudo = "only_sudo", "sudo su"
    only_su = "only_su", "su"
    enable = "enable", "enable"
    super = "super", "super 15"
    super_level = "super_level", "super level 15"

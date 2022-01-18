from django.utils.translation import gettext


def translate_value(value):
    if not value:
        return value
    sps = ['. ', ': ']
    spb = {str(sp in value): sp for sp in sps}
    sp = spb.get('True')
    if not sp:
        return value

    tpl, data = value.split(sp, 1)
    return gettext(tpl + sp) + data

from django.utils.translation import gettext, gettext_noop


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


def i18n_fmt(tpl, *args):
    if '%' not in tpl:
        raise ValueError('Invalid template, should contains %')
    if not args:
        return tpl

    args = [str(arg) for arg in args]

    try:
        tpl % tuple(args)
    except TypeError:
        raise ValueError('Invalid template, args not match: {} {}'.format(tpl, args))
    return tpl + ' % ' + ', '.join(args)


def i18n_trans(s):
    if ' % ' not in s:
        return gettext(s)
    tpl, args = s.split(' % ', 1)
    args = args.split(', ')
    args = [gettext(arg) for arg in args]
    try:
        return gettext(tpl) % tuple(args)
    except TypeError:
        return gettext(tpl)


def hello():
    log = i18n_fmt(gettext_noop('Hello %s'), 'world')
    print(i18n_trans(log))

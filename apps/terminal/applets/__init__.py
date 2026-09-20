import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def install_or_update_builtin_applets():
    from terminal.models import Applet

    applets = os.listdir(BASE_DIR)
    for d in applets:
        path = os.path.join(BASE_DIR, d)
        if not os.path.isdir(path) or not os.path.exists(os.path.join(path, 'manifest.yml')):
            continue
        try:
            if Applet.install_from_dir(path):
                print("Install or update applet: {}".format(path))
        except Exception as e:
            print(e)


if __name__ == '__main__':
    install_or_update_builtin_applets()

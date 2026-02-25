from django.conf import settings

from .device import Device

DEFAULT_DRIVER_PATH = "./lib/libpiico_ccmu.so"


def open_piico_device(driver_path=None) -> Device:
    if driver_path is None:
        driver_path = settings.PIICO_DRIVER_PATH or DEFAULT_DRIVER_PATH
    d = Device()
    d.open(driver_path)
    return d

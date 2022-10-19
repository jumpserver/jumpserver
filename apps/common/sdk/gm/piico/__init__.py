from .device import Device


def open_piico_device(driver_path) -> Device:
    d = Device()
    d.open(driver_path)
    return d

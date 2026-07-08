from ..base.device import Device


class CCUPMDevice(Device):
    name = "ccupm"

    def __init__(self):
        self.open()

    def open(self, driver_path="libsdf_crypto.so"):
        super().open(driver_path)

    def reset_key_store(self):
        pass

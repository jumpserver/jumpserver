from ..base.device import Device


class PiicoDevice(Device):
    name = "piico"

    def __init__(self):
        self.open()

    # 默认去lib路径检索
    def open(self, driver_path="libpiico_ccmu.so"):
        super().open(driver_path)
from .base.device import Device
from enum import Enum

from common.sdk.gm import piico, ccupm, sctu


class CryptoVendor(Enum):
    PIICO = "piico"
    CCUPM = "ccupm"
    SCTU = "sctu"

    @classmethod
    def from_str(cls, name: str | None):
        if name is None or not name.strip():
            return cls.PIICO

        name = name.strip().lower()
        for vendor in cls:
            if name in (vendor.name.lower(), vendor.value.lower()):
                return vendor
        raise ValueError(f"Unknown GM Vendor: {name}")


def open_gm_device(vendor: CryptoVendor) -> Device:
    if vendor is CryptoVendor.CCUPM:
        return ccupm.CCUPMDevice()
    elif vendor is CryptoVendor.SCTU:
        return sctu.SCTUDevice()
    else:
        return piico.PiicoDevice()

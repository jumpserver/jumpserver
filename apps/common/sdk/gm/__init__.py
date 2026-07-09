from .base.device import Device
from enum import Enum

from common.sdk.gm import piico, ccupm, sctu


class CryptoVendor(Enum):
    PIICO = "piico"
    CCUPM = "ccupm"
    SCTU = "sctu"

    @classmethod
    def from_str(cls, name: str):
        try:
            return cls[name.upper()]
        except KeyError:
            for vendor in cls:
                if vendor.value.lower() == name.lower():
                    return vendor
            raise ValueError(f"Unknown GM Vendor: {name}")


def open_gm_device(vendor: CryptoVendor) -> Device:
    if vendor is CryptoVendor.CCUPM:
        return ccupm.CCUPMDevice()
    elif vendor is CryptoVendor.SCTU:
        return sctu.SCTUDevice()
    else:
        return piico.PiicoDevice()

from typing import Dict, Tuple
from ..models.enums import BrowserFamily, DeviceType, OSType

# Map the raw keys from market_share.json to semantic Enums.
# Tuple structure: (BrowserFamily, DefaultDeviceType, ForcedOSType)
# If OSType is UNKNOWN, it implies it must be inferred dynamically (e.g., Desktop Chrome can be Win/Mac/Linux).

MARKET_KEY_MAP: Dict[str, Tuple[BrowserFamily, DeviceType, OSType]] = {
    "and_chr": (BrowserFamily.CHROME, DeviceType.MOBILE, OSType.ANDROID),
    "and_ff":  (BrowserFamily.FIREFOX, DeviceType.MOBILE, OSType.ANDROID),
    "and_uc":  (BrowserFamily.UC, DeviceType.MOBILE, OSType.ANDROID),
    "android": (BrowserFamily.CHROME, DeviceType.MOBILE, OSType.ANDROID), # Generic Android often implies WebKit/Chrome
    "chrome":  (BrowserFamily.CHROME, DeviceType.DESKTOP, OSType.UNKNOWN),
    "edge":    (BrowserFamily.EDGE, DeviceType.DESKTOP, OSType.UNKNOWN),
    "firefox": (BrowserFamily.FIREFOX, DeviceType.DESKTOP, OSType.UNKNOWN),
    "ie":      (BrowserFamily.IE, DeviceType.DESKTOP, OSType.WINDOWS),     # IE is always Windows
    "ios_saf": (BrowserFamily.SAFARI, DeviceType.MOBILE, OSType.IOS),
    "op_mob":  (BrowserFamily.OPERA, DeviceType.MOBILE, OSType.ANDROID),
    "samsung": (BrowserFamily.SAMSUNG, DeviceType.MOBILE, OSType.ANDROID),
}

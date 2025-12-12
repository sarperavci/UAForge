from dataclasses import dataclass, field
from typing import List, Optional, Dict
from .enums import DeviceType, OSType, BrowserFamily, EngineType


@dataclass(frozen=True)
class HardwareInfo:
    """
    Represents the physical hardware logic.
    e.g., Device Type, Manufacturer Model (Pixel 6), CPU Architecture (arm64).
    """
    device_type: DeviceType
    model: Optional[str] = None          # e.g. "SM-G991B"
    brand_header_value: Optional[str] = None # e.g. '"Google Pixel 7";v="115"'
    cpu_arch: str = "x86_64"             # x86_64, arm64


@dataclass(frozen=True)
class OSInfo:
    """
    Represents the Operating System logic.
    e.g., Windows 10, Android 13.
    """
    type: OSType
    version: str                         # "10.0", "13", "14.2.1"
    platform_header: str                 # Sec-CH-UA-Platform: "Windows"
    ua_string_token: str                 # The part inside the UA parentheses


@dataclass(frozen=True)
class BrowserInfo:
    """
    Represents the Browser Software logic.
    e.g., Chrome 142, Firefox 144.
    """
    family: BrowserFamily
    version_major: str
    version_full: str                    # "142.0.4567.89"
    engine: EngineType
    


@dataclass
class UserAgentData:
    """
    The final product.
    Contains the legacy User-Agent string and the modern Client Hints.
    """
    # Legacy Header
    user_agent: str

    # Metadata for debugging/verification (required)
    meta_os: OSType
    meta_browser: BrowserFamily
    meta_device: DeviceType

    # Modern Client Hints (Sec-CH-UA*)
    # If these are empty strings, it implies the browser (Safari/Firefox) does not support them.
    ch_brands: str            # Sec-CH-UA
    ch_full_version_list: str # Sec-CH-UA-Full-Version-List
    ch_mobile: str            # Sec-CH-UA-Mobile
    ch_platform: str          # Sec-CH-UA-Platform
    ch_platform_version: str  # Sec-CH-UA-Platform-Version
    ch_model: str             # Sec-CH-UA-Model
    ch_arch: str              # Sec-CH-UA-Arch
    ch_bitness: str           # Sec-CH-UA-Bitness

    def get_headers(self) -> Dict[str, str]:
        """Returns a dictionary of all relevant HTTP headers."""
        headers: Dict[str, str] = {"User-Agent": self.user_agent}

        # Only include client hints if they were generated
        if self.ch_brands:
            headers["Sec-CH-UA"] = self.ch_brands
        if self.ch_mobile:
            headers["Sec-CH-UA-Mobile"] = self.ch_mobile
        if self.ch_platform:
            headers["Sec-CH-UA-Platform"] = f'"{self.ch_platform}"'
        if self.ch_full_version_list:
            headers["Sec-CH-UA-Full-Version-List"] = self.ch_full_version_list
        return headers
    
    def get_all_client_hints(self) -> Dict[str, str]:
        """Returns only the Client Hints headers."""
        headers: Dict[str, str] = {}

        if self.ch_brands:
            headers["Sec-CH-UA"] = self.ch_brands
        if self.ch_mobile:
            headers["Sec-CH-UA-Mobile"] = self.ch_mobile
        if self.ch_platform:
            headers["Sec-CH-UA-Platform"] = f'"{self.ch_platform}"'
        if self.ch_full_version_list:
            headers["Sec-CH-UA-Full-Version-List"] = self.ch_full_version_list
        if self.ch_platform_version:
            headers["Sec-CH-UA-Platform-Version"] = self.ch_platform_version
        if self.ch_model:
            headers["Sec-CH-UA-Model"] = f'"{self.ch_model}"'
        if self.ch_arch:
            headers["Sec-CH-UA-Arch"] = f'"{self.ch_arch}"'
        if self.ch_bitness:
            headers["Sec-CH-UA-Bitness"] = f'"{self.ch_bitness}"'

        return headers

     

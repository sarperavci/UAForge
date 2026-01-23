import random
from typing import List, Tuple, Optional, TYPE_CHECKING
from ..models.enums import BrowserFamily, DeviceType

if TYPE_CHECKING:
    from ..data.loader import DataLoader


class ClientHintsGenerator:
    """
    Generates the modern 'Sec-CH-UA' headers.
    """
    
    # General GREASE token
    GREASE_BRAND = list("Not A Brand")
    PUNCT = ";:()_ "
    _brand_base_cache = {}
    
    @staticmethod
    def _format_brand_list(brands: List[Tuple[str, str]]) -> str:
        parts = []
        for brand, version in brands:
            parts.append(f'"{brand}";v="{version}"')
        return ", ".join(parts)

    @classmethod
    def _get_brand_tuples(cls, family: BrowserFamily, version: str, rand=None) -> List[Tuple[str, str]]:
        """Randomized brand tuples. Accepts an optional RNG instance for faster and thread-safe sampling."""
        if rand is None:
            rand = random

        brands: List[Tuple[str, str]] = []
        name = cls.GREASE_BRAND.copy()
        space_idxs = [i for i, c in enumerate(name) if c == " "]

        if len(space_idxs) >= 2:
            sep1, sep2 = rand.choices(cls.PUNCT, k=2)
            name[space_idxs[0]] = sep1
            name[space_idxs[1]] = sep2

        grease_name = "".join(name)
        grease_version = rand.choice(("99", "8", "24"))
        brands.append((grease_name, grease_version))

        if family == BrowserFamily.CHROME:
            brands.append(("Chromium", version))
            brands.append(("Google Chrome", version))
        elif family == BrowserFamily.EDGE:
            brands.append(("Chromium", version))
            brands.append(("Microsoft Edge", version))
        elif family == BrowserFamily.OPERA:
            brands.append(("Chromium", version))
            brands.append(("Opera", version))
        else:
            brands.append(("Chromium", version))
        
        # Shuffle to randomize order
        rand.shuffle(brands)
        
        return brands

    @classmethod
    def generate_brands(cls, family: BrowserFamily, major_version: str, rand=None) -> str:
        """
        Constructs the Sec-CH-UA header value (Major versions only).
        Returns EMPTY STRING for Safari/Firefox.

        For Edge and Opera, uses appropriate Chromium major version:
        - Edge: Same major version as Edge
        - Opera: Opera major version + 16
        """
        if family in (BrowserFamily.FIREFOX, BrowserFamily.SAFARI):
            return ""

        # Get Chromium major version for Edge and Opera
        chromium_major = None
        if family == BrowserFamily.EDGE:
            chromium_major = major_version  # Edge uses same major as Chromium
        elif family == BrowserFamily.OPERA:
            try:
                chromium_major = str(int(major_version) + 16)
            except ValueError:
                chromium_major = major_version

        # Build the brand list
        parts = []
        parts.append('"Not A Brand";v="99"')

        if family == BrowserFamily.CHROME:
            parts.append(f'"Chromium";v="{major_version}"')
            parts.append(f'"Google Chrome";v="{major_version}"')
        elif family == BrowserFamily.EDGE:
            parts.append(f'"Chromium";v="{chromium_major}"')
            parts.append(f'"Microsoft Edge";v="{major_version}"')
        elif family == BrowserFamily.OPERA:
            parts.append(f'"Chromium";v="{chromium_major}"')
            parts.append(f'"Opera";v="{major_version}"')
        else:
            parts.append(f'"Chromium";v="{major_version}"')

        return ", ".join(parts)

    @classmethod
    def get_major_chromium_full_version(cls, family: BrowserFamily, full_version: str, rand=None, loader: Optional['DataLoader'] = None) -> Optional[int]:
        chromium_version = None
        if loader:
            if family == BrowserFamily.EDGE:
                try:
                    major = full_version.split('.')[0]
                    chromium_version = loader.get_chromium_version_for_edge(major)
                except Exception:
                    pass
            elif family == BrowserFamily.OPERA:
                try:
                    major = full_version.split('.')[0]
                    chromium_version = loader.get_chromium_version_for_opera(major)
                except Exception:
                    pass
        if chromium_version:
            return int(chromium_version.split('.')[0])
        elif family == BrowserFamily.CHROME:
            return int(full_version.split('.')[0])
        return -1
        
    
    @classmethod
    def generate_full_version_list(cls, family: BrowserFamily, full_version: str, rand=None, loader: Optional['DataLoader'] = None) -> str:
        """
        Constructs the Sec-CH-UA-Full-Version-List header.
        Returns EMPTY STRING for Safari/Firefox.

        For Edge and Opera, uses appropriate Chromium version:
        - Edge: Same major version as Edge
        - Opera: Opera major version + 16
        """
        if family in (BrowserFamily.FIREFOX, BrowserFamily.SAFARI):
            return ""

        # Get Chromium version for Edge and Opera
        chromium_version = None
        if loader:
            if family == BrowserFamily.EDGE:
                try:
                    major = full_version.split('.')[0]
                    chromium_version = loader.get_chromium_version_for_edge(major)
                except Exception:
                    pass
            elif family == BrowserFamily.OPERA:
                try:
                    major = full_version.split('.')[0]
                    chromium_version = loader.get_chromium_version_for_opera(major)
                except Exception:
                    pass

        # Build the version list
        parts = []
        parts.append('"Not A Brand";v="99.0.0.0"')

        if family == BrowserFamily.CHROME:
            parts.append(f'"Chromium";v="{full_version}"')
            parts.append(f'"Google Chrome";v="{full_version}"')
        elif family == BrowserFamily.EDGE:
            if chromium_version:
                parts.append(f'"Chromium";v="{chromium_version}"')
            else:
                parts.append(f'"Chromium";v="{full_version}"')
            parts.append(f'"Microsoft Edge";v="{full_version}"')
        elif family == BrowserFamily.OPERA:
            if chromium_version:
                parts.append(f'"Chromium";v="{chromium_version}"')
            else:
                # Fallback: calculate Chromium version
                major = int(full_version.split('.')[0])
                chromium_major = major + 16
                parts.append(f'"Chromium";v="{chromium_major}.0.0.0"')
            parts.append(f'"Opera";v="{full_version}"')
        else:
            parts.append(f'"Chromium";v="{full_version}"')

        return ", ".join(parts)

    @staticmethod
    def get_mobile_token(is_mobile: bool) -> str:
        return "?1" if is_mobile else "?0"

    @staticmethod
    def get_platform_token(platform: str) -> str:
        return platform

    @classmethod
    def generate_full_version(cls, family: BrowserFamily, full_version: str) -> str:
        """
        Constructs the Sec-CH-UA-Full-Version header.
        Returns EMPTY STRING for Safari/Firefox.
        """
        if family in (BrowserFamily.FIREFOX, BrowserFamily.SAFARI):
            return ""

        # Return the full version as-is (e.g., "142.0.7444.175")
        return full_version

    @classmethod
    def generate_form_factors(cls, device_type: DeviceType, rand=None) -> str:
        """
        Constructs the Sec-CH-UA-Form-Factors header.
        """
        if rand is None:
            rand = random

        if device_type == DeviceType.DESKTOP:
            return "Desktop"
        elif device_type == DeviceType.TABLET:
            return "Tablet"
        else:  # MOBILE
            return "Mobile"

    @staticmethod
    def get_wow64_token(is_wow64: bool) -> str:
        """
        Constructs the Sec-CH-UA-WoW64 header.
        """
        return "?1" if is_wow64 else "?0"

    @staticmethod
    def get_prefers_color_scheme(rand=None) -> str:
        """
        Constructs the Sec-CH-Prefers-Color-Scheme header.
        """
        if rand is None:
            rand = random
        # Randomly choose between light and dark themes
        return rand.choice(["light", "dark"])

import random
from typing import List, Tuple
from ..models.enums import BrowserFamily


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
        elif family == BrowserFamily.SAMSUNG:
            brands.append(("Chromium", version))
            brands.append(("Samsung Internet", version))
        elif family == BrowserFamily.UC:
            brands.append(("Chromium", version))
            brands.append(("UC Browser", version))
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
        """
        if family in (BrowserFamily.FIREFOX, BrowserFamily.SAFARI):
            return ""

        # Fast path: use cached base brand names and format with provided version.
        key = (family, 'major')
        base = cls._brand_base_cache.get(key)
        if base is None:
            # Build deterministic base list (without grease punctuation variation) and cache it.
            base = []
            base.append(("Not A Brand", "99"))
            if family == BrowserFamily.CHROME:
                base.append(("Chromium", None))
                base.append(("Google Chrome", None))
            elif family == BrowserFamily.EDGE:
                base.append(("Chromium", None))
                base.append(("Microsoft Edge", None))
            elif family == BrowserFamily.OPERA:
                base.append(("Chromium", None))
                base.append(("Opera", None))
            elif family == BrowserFamily.SAMSUNG:
                base.append(("Chromium", None))
                base.append(("Samsung Internet", None))
            elif family == BrowserFamily.UC:
                base.append(("Chromium", None))
                base.append(("UC Browser", None))
            else:
                base.append(("Chromium", None))

            cls._brand_base_cache[key] = base

        # Format with the major version
        parts = []
        for name, v in base:
            version = v if v is not None else major_version
            parts.append(f'"{name}";v="{version}"')
        return ", ".join(parts)

    @classmethod
    def generate_full_version_list(cls, family: BrowserFamily, full_version: str, rand=None) -> str:
        """
        Constructs the Sec-CH-UA-Full-Version-List header.
        Returns EMPTY STRING for Safari/Firefox.
        """
        if family in (BrowserFamily.FIREFOX, BrowserFamily.SAFARI):
            return ""

        # Use the same base cached brand names as major but format with full_version
        key = (family, 'major')
        base = cls._brand_base_cache.get(key)
        if base is None:
            # fall back to generate_brands which will populate cache
            cls.generate_brands(family, full_version)
            base = cls._brand_base_cache.get(key)

        parts = []
        for name, v in base:
            version = v if v is not None else full_version
            parts.append(f'"{name}";v="{version}"')
        return ", ".join(parts)

    @staticmethod
    def get_mobile_token(is_mobile: bool) -> str:
        return "?1" if is_mobile else "?0"

    @staticmethod
    def get_platform_token(platform: str) -> str:
        return platform

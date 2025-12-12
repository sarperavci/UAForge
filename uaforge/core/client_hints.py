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
    
    @staticmethod
    def _format_brand_list(brands: List[Tuple[str, str]]) -> str:
        parts = []
        for brand, version in brands:
            parts.append(f'"{brand}";v="{version}"')
        return ", ".join(parts)

    @classmethod
    def _get_brand_tuples(cls, family: BrowserFamily, version: str) -> List[Tuple[str, str]]:
        brands: List[Tuple[str, str]] = []
        name = cls.GREASE_BRAND.copy()
        space_idxs = [i for i, c in enumerate(name) if c == " "]

        if len(space_idxs) >= 2:
            sep1, sep2 = random.choices(cls.PUNCT, k=2)
            name[space_idxs[0]] = sep1
            name[space_idxs[1]] = sep2

        grease_name = "".join(name)
        grease_version = random.choice(("99", "8", "24"))
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
        random.shuffle(brands)
        
        return brands

    @classmethod
    def generate_brands(cls, family: BrowserFamily, major_version: str) -> str:
        """
        Constructs the Sec-CH-UA header value (Major versions only).
        Returns EMPTY STRING for Safari/Firefox.
        """
        if family in (BrowserFamily.FIREFOX, BrowserFamily.SAFARI):
            return ""
        brands = cls._get_brand_tuples(family, major_version)
        return cls._format_brand_list(brands)

    @classmethod
    def generate_full_version_list(cls, family: BrowserFamily, full_version: str) -> str:
        """
        Constructs the Sec-CH-UA-Full-Version-List header.
        Returns EMPTY STRING for Safari/Firefox.
        """
        if family in (BrowserFamily.FIREFOX, BrowserFamily.SAFARI):
            return ""
        brands = cls._get_brand_tuples(family, full_version)
        return cls._format_brand_list(brands)

    @staticmethod
    def get_mobile_token(is_mobile: bool) -> str:
        return "?1" if is_mobile else "?0"

    @staticmethod
    def get_platform_token(platform: str) -> str:
        return platform

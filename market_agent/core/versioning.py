import random
from typing import Tuple
from ..models.enums import BrowserFamily


class VersionExpander:
    """
    Expands a simple major version string (e.g., "142") into a full realistic version string
    """

    @staticmethod
    def generate_full_version(family: BrowserFamily, major_version: str) -> str:
        if "." in major_version:
            parts = major_version.split('.')
            if len(parts) > 1:
                return major_version
        
        if family in (BrowserFamily.CHROME, BrowserFamily.EDGE, BrowserFamily.OPERA, BrowserFamily.SAMSUNG, BrowserFamily.UC):
            try:
                major_int = int(major_version)
            except ValueError:
                return f"{major_version}.0.0.0"

            # Rough heuristic: Chrome build numbers increase over time.
            # v100 ~ build 4896. v130 ~ build 6723.
            # Slope approx: 60 build units per major version.
            estimated_build = 4000 + (major_int - 80) * 60
            build = random.randint(estimated_build, estimated_build + 100)
            patch = random.randint(0, 200)
            return f"{major_version}.0.{build}.{patch}"

        elif family == BrowserFamily.FIREFOX:
            # Firefox Strategy: Major.0
            return f"{major_version}.0"

        elif family == BrowserFamily.SAFARI:
            # Safari: return marketing version as-is; templates will use it
            return major_version

        # Fallback
        return f"{major_version}.0"

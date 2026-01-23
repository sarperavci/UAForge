import random
from typing import Tuple, Optional, TYPE_CHECKING
from ..models.enums import BrowserFamily

if TYPE_CHECKING:
    from ..data.loader import DataLoader


class VersionExpander:
    """
    Expands a simple major version string (e.g., "142") into a full realistic version string
    """

    @staticmethod
    def generate_full_version(
        family: BrowserFamily,
        major_version: str,
        rand=None,
        platform: Optional[str] = None,
        loader: Optional['DataLoader'] = None
    ) -> str:
        """
        Generate a full version string for a given browser family and major version.

        Args:
            family: Browser family enum
            major_version: Major version number (e.g., "142")
            rand: Random generator instance (optional)
            platform: Platform name for Chrome ("windows", "macos", "linux")

        Returns:
            Full version string (e.g., "142.0.6345.78")
        """
        if "." in major_version:
            parts = major_version.split('.')
            if len(parts) > 1:
                return major_version

        if rand is None:
            rand = random

        if family == BrowserFamily.CHROME:
            return VersionExpander._get_chrome_version(major_version, platform, rand, loader)

        elif family == BrowserFamily.EDGE:
            return VersionExpander._get_edge_version(major_version, platform, rand, loader)

        elif family == BrowserFamily.OPERA:
            return VersionExpander._get_opera_version(major_version, platform, rand, loader)

        elif family == BrowserFamily.FIREFOX:
            return f"{major_version}.0"

        elif family == BrowserFamily.SAFARI:
            return major_version

        # Fallback
        return f"{major_version}.0"

    @staticmethod
    def _get_chrome_version(major_version: str, platform: Optional[str], rand:random.Random, loader: Optional['DataLoader']) -> str:
        """
        Get a real Chrome version from scraped data.

        Args:
            major_version: Major version number
            platform: Platform name ("windows", "macos", "linux")
            rand: Random generator instance
            loader: DataLoader instance

        Returns:
            Full Chrome version string
        """
        if not loader:
            return f"{major_version}.0.0.0"

        try:
            # Default to windows if no platform specified
            if platform is None:
                platform = "windows"

            # Get available versions for this major version
            versions = loader.get_chrome_versions(major_version, platform)

            if versions:
                # Randomly select one of the available versions
                return rand.choice(versions)
            else:
                return f"{major_version}.0.0.0"

        except Exception:
            return f"{major_version}.0.0.0"
    @staticmethod
    def _get_edge_version(major_version: str, platform: Optional[str], rand:random.Random, loader: Optional['DataLoader']) -> str:
        """
        Get a real Edge version from scraped data.

        Args:
            major_version: Major version number
            platform: Platform name ("windows", "macos", "linux")
            rand: Random generator instance
            loader: DataLoader instance

        Returns:
            Full Edge version string
        """
        if not loader:
            return f"{major_version}.0.0.0"

        try:
            # Default to windows if no platform specified
            if platform is None:
                platform = "windows"

            # Get available versions for this major version
            versions = loader.get_edge_versions(major_version, platform)

            if versions:
                # Randomly select one of the available versions
                return rand.choice(versions)
            else:
                return f"{major_version}.0.0.0"

        except Exception:
            return f"{major_version}.0.0.0"

    @staticmethod
    def _get_opera_version(major_version: str, platform: Optional[str], rand: random.Random, loader: Optional['DataLoader']) -> str:
        """
        Get a real Opera version from scraped data.

        Args:
            major_version: Major version number
            platform: Platform name ("windows", "macos", "linux")
            rand: Random generator instance
            loader: DataLoader instance

        Returns:
            Full Opera version string
        """
        if not loader:
            return f"{major_version}.0.0.0"

        try:
            # Default to windows if no platform specified
            if platform is None:
                platform = "windows"

            # Get available versions for this major version
            versions = loader.get_opera_versions(major_version, platform)

            if versions:
                # Randomly select one of the available versions
                return rand.choice(versions)
            else:
                return f"{major_version}.0.0.0"

        except Exception:
            return f"{major_version}.0.0.0"

#!/usr/bin/env python3

import json
import urllib.request
from typing import Dict, List, Set
from pathlib import Path


BASE_URL = "https://versionhistory.googleapis.com/v1"

# Platforms we care about
PLATFORMS = {
    "windows": ["win", "win64"],
    "macos": ["mac", "mac_arm64"],
    "linux": ["linux"]
}


def fetch_versions(platform: str) -> List[str]:
    """
    Fetch stable Chrome versions for a specific platform.

    Args:
        platform: Platform identifier (e.g., 'win', 'mac', 'linux')

    Returns:
        List of version strings
    """
    url = f"{BASE_URL}/chrome/platforms/{platform}/channels/stable/versions"

    print(f"Fetching versions for {platform}...")

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())

        versions = []
        if "versions" in data:
            for version_obj in data["versions"]:
                version = version_obj.get("version", "")
                # Filter out unknown_version entries
                if version and version != "unknown_version":
                    versions.append(version)

        print(f"  Found {len(versions)} versions for {platform}")
        return versions

    except Exception as e:
        print(f"  Error fetching {platform}: {e}")
        return []


def extract_versions_by_major(versions: List[str]) -> Dict[str, List[str]]:
    """
    Group versions by major version number.

    Args:
        versions: List of version strings (e.g., ["89.0.4389.72", "88.0.4324.190"])

    Returns:
        Dictionary mapping major version to list of full versions
    """
    by_major = {}

    for version in versions:
        try:
            major = version.split('.')[0]
            if major not in by_major:
                by_major[major] = []
            by_major[major].append(version)
        except (ValueError, IndexError):
            continue

    return by_major


def main():
    """Main script execution."""
    all_versions = {}

    # Fetch versions for all platforms
    for os_name, platform_list in PLATFORMS.items():
        os_versions = []

        for platform in platform_list:
            versions = fetch_versions(platform)
            os_versions.extend(versions)

        # Remove duplicates and sort
        unique_versions = sorted(list(set(os_versions)), reverse=True)

        # Group by major version
        by_major = extract_versions_by_major(unique_versions)

        all_versions[os_name] = {
            "all_versions": unique_versions[:100],  # Keep last 100 versions
            "by_major_version": by_major
        }

        print(f"\n{os_name}: {len(unique_versions)} unique versions")
        print(f"  Major versions: {sorted(by_major.keys(), reverse=True)[:10]}")

    # Save to data directory
    output_path = Path(__file__).parent.parent / "uaforge" / "data" / "chrome_versions.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_versions, f, separators=(',', ':'), ensure_ascii=False)

    print(f"\n✓ Saved Chrome versions to {output_path}")

    # Print summary
    print("\nSummary:")
    for os_name, data in all_versions.items():
        major_versions = list(data["by_major_version"].keys())
        print(f"  {os_name}: {len(data['all_versions'])} versions, "
              f"major versions {min(major_versions)}-{max(major_versions)}")


if __name__ == "__main__":
    main()

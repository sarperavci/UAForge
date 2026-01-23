#!/usr/bin/env python3

import json
import re
import urllib.request
from typing import Dict, List
from pathlib import Path


OPERA_URL = "https://get.opera.com/pub/opera/desktop/"


def fetch_opera_versions() -> List[str]:
    """
    Fetch Opera versions from directory listing.

    Returns:
        List of version strings
    """
    print(f"Fetching Opera versions from {OPERA_URL}...")

    try:
        with urllib.request.urlopen(OPERA_URL) as response:
            content = response.read().decode('utf-8')

        # Parse directory listing for version numbers
        # Pattern: <a href="100.0.4815.20/">100.0.4815.20/</a>
        pattern = r'<a href="([\d.]+)/">([\d.]+)/</a>'
        matches = re.finditer(pattern, content)

        versions = []
        for match in matches:
            version = match.group(1)
            if version and version.count('.') == 3:  # Ensure it's a full version
                versions.append(version)

        print(f"  Found {len(versions)} Opera versions")
        return sorted(versions, reverse=True)

    except Exception as e:
        print(f"  Error fetching Opera versions: {e}")
        return []


def organize_versions_by_major(versions: List[str]) -> Dict[str, List[str]]:
    """
    Group versions by major version number.

    Args:
        versions: List of version strings

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
    print("Fetching Opera stable versions...\n")

    versions = fetch_opera_versions()

    if not versions:
        print("\n✗ No versions found. Exiting.")
        return

    # Organize by major version
    by_major = organize_versions_by_major(versions)

    # Create result structure (same for all platforms)
    result = {
        "windows": {
            "all_versions": versions[:100],  # Keep last 100 versions
            "by_major_version": by_major
        },
        "macos": {
            "all_versions": versions[:100],
            "by_major_version": by_major
        },
        "linux": {
            "all_versions": versions[:100],
            "by_major_version": by_major
        }
    }

    # Save to data directory
    output_path = Path(__file__).parent.parent / "uaforge" / "data" / "opera_versions.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, separators=(',', ':'), ensure_ascii=False)

    print(f"\n✓ Saved Opera versions to {output_path}")

    # Print summary
    print("\nSummary:")
    print(f"  Total unique versions: {len(versions)}")
    major_versions = sorted(by_major.keys(), key=int, reverse=True)
    print(f"  Major versions: {major_versions[:10]}")
    if major_versions:
        print(f"  Latest version: {by_major[major_versions[0]][0]}")
        latest_major = int(major_versions[0])
        chromium_major = latest_major + 16
        print(f"  Corresponding Chromium major: {chromium_major}")


if __name__ == "__main__":
    main()

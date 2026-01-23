#!/usr/bin/env python3

import json
import re
import urllib.request
from typing import Dict, List, Set
from pathlib import Path


# URLs for Edge release notes
CURRENT_URL = "https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-stable-channel"
ARCHIVE_URL = "https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-archive-stable-channel"


def fetch_page_content(url: str) -> str:
    """
    Fetch content from a URL.

    Args:
        url: URL to fetch

    Returns:
        Page content as string
    """
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""


def extract_edge_versions(content: str) -> List[str]:
    """
    Extract Edge version numbers from page content.

    Args:
        content: HTML/text content

    Returns:
        List of version strings
    """
    # Pattern to match Edge versions (e.g., 144.0.3719.82, 143.0.3650.139)
    # Match versions in format: X.Y.Z.W or "Version X.Y.Z.W"
    patterns = [
        r'Version\s+(\d{2,3}\.\d+\.\d+\.\d+)',  # "Version 144.0.3719.82"
        r'\b(\d{2,3}\.\d+\.\d+\.\d+)\b',  # Direct version numbers
    ]

    versions = set()

    for pattern in patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            version = match.group(1)
            # Filter out obviously wrong versions (e.g., dates like 2025.12.18)
            parts = version.split('.')
            if len(parts) == 4:
                major = int(parts[0])
                # Edge stable versions are typically between 80 and 200
                if 80 <= major <= 200:
                    versions.add(version)

    return sorted(list(versions), reverse=True)


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
    print("Fetching Microsoft Edge stable versions...\n")

    all_versions = set()

    # Fetch from current release notes
    print(f"Fetching from current release notes...")
    current_content = fetch_page_content(CURRENT_URL)
    if current_content:
        current_versions = extract_edge_versions(current_content)
        all_versions.update(current_versions)
        print(f"  Found {len(current_versions)} versions from current page")

    # Fetch from archived release notes
    print(f"Fetching from archived release notes...")
    archive_content = fetch_page_content(ARCHIVE_URL)
    if archive_content:
        archive_versions = extract_edge_versions(archive_content)
        all_versions.update(archive_versions)
        print(f"  Found {len(archive_versions)} versions from archive page")

    if not all_versions:
        print("\n✗ No versions found. Exiting.")
        return

    # Convert to sorted list
    all_versions_list = sorted(list(all_versions), reverse=True)

    # Organize by major version
    by_major = organize_versions_by_major(all_versions_list)

    # Create result structure (same for all platforms)
    result = {
        "windows": {
            "all_versions": all_versions_list[:100],  # Keep last 100 versions
            "by_major_version": by_major
        },
        "macos": {
            "all_versions": all_versions_list[:100],
            "by_major_version": by_major
        },
        "linux": {
            "all_versions": all_versions_list[:100],
            "by_major_version": by_major
        }
    }

    # Save to data directory
    output_path = Path(__file__).parent.parent / "uaforge" / "data" / "edge_versions.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, separators=(',', ':'), ensure_ascii=False)

    print(f"\n✓ Saved Edge versions to {output_path}")

    # Print summary
    print("\nSummary:")
    print(f"  Total unique versions: {len(all_versions)}")
    major_versions = sorted(by_major.keys(), key=int, reverse=True)
    print(f"  Major versions: {major_versions[:10]}")
    if major_versions:
        print(f"  Latest version: {by_major[major_versions[0]][0]}")


if __name__ == "__main__":
    main()

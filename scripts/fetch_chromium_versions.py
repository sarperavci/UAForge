#!/usr/bin/env python3

import json
import urllib.request
from typing import Dict, List
from pathlib import Path


BASE_URL = "https://chromiumdash.appspot.com/fetch_releases"

# Platforms to fetch
PLATFORMS = ["Windows", "Linux", "Mac", "Android", "iOS"]


def fetch_chromium_versions(platform: str, num: int = 1000) -> List[Dict]:
    """
    Fetch Chromium versions for a specific platform.

    Args:
        platform: Platform identifier (e.g., 'Windows', 'Mac', 'Linux')
        num: Number of versions to fetch

    Returns:
        List of version dictionaries
    """
    url = f"{BASE_URL}?channel=Stable&platform={platform}&num={num}"

    print(f"Fetching {num} Chromium versions for {platform}...")

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())

        print(f"  Found {len(data)} versions for {platform}")
        return data

    except Exception as e:
        print(f"  Error fetching {platform}: {e}")
        return []


def process_chromium_data(all_data: Dict[str, List[Dict]]) -> Dict:
    """
    Process raw Chromium data and organize by platform and major version.

    Args:
        all_data: Dictionary mapping platform names to version lists

    Returns:
        Processed dictionary with versions organized by platform and major version
    """
    result = {
        "by_major_version": {},
        "platforms": {}
    }

    # Collect all versions across all platforms
    all_versions = {}

    for platform, versions in all_data.items():
        platform_versions = []

        for v in versions:
            version = v.get("version", "")
            if not version:
                continue

            major = str(v.get("milestone", ""))

            # Store version with metadata
            version_data = {
                "version": version,
                "platform": platform,
                "milestone": major
            }

            platform_versions.append(version_data)

            # Group by major version
            if major not in all_versions:
                all_versions[major] = []

            if version not in [v["version"] for v in all_versions[major]]:
                all_versions[major].append(version_data)

        result["platforms"][platform.lower()] = platform_versions

    # Organize by major version
    for major, versions in all_versions.items():
        # Deduplicate and extract just the version strings
        unique_versions = sorted(list(set([v["version"] for v in versions])), reverse=True)
        result["by_major_version"][major] = unique_versions

    return result


def main():
    """Main script execution."""
    print("Fetching Chromium stable versions from Chromium Dash API...\n")

    all_data = {}

    # Fetch versions for all platforms
    for platform in PLATFORMS:
        versions = fetch_chromium_versions(platform, num=1000)
        if versions:
            all_data[platform] = versions

    if not all_data:
        print("\n✗ No data fetched. Exiting.")
        return

    # Process and organize the data
    processed_data = process_chromium_data(all_data)

    # Save to data directory
    output_path = Path(__file__).parent.parent / "uaforge" / "data" / "chromium_versions.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, separators=(',', ':'), ensure_ascii=False)

    print(f"\n✓ Saved Chromium versions to {output_path}")

    # Print summary
    print("\nSummary:")
    major_versions = sorted(processed_data["by_major_version"].keys(), key=int, reverse=True)
    print(f"  Total major versions: {len(major_versions)}")
    print(f"  Latest major: {major_versions[0] if major_versions else 'N/A'}")
    print(f"  Oldest major: {major_versions[-1] if major_versions else 'N/A'}")
    print(f"  Total unique versions: {sum(len(v) for v in processed_data['by_major_version'].values())}")


if __name__ == "__main__":
    main()

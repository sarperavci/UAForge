#!/usr/bin/env python3

import json
import urllib.request
import re
from typing import Dict, List, Set
from pathlib import Path


BASE_PATH = Path(__file__).parent.parent / "uaforge" / "data"


def load_existing_data(filename: str) -> Dict:
    """Load existing version data."""
    file_path = BASE_PATH / filename
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_data(filename: str, data: Dict) -> bool:
    """
    Save data as minified JSON only if it has changed.

    Returns:
        True if data was saved (changed), False if no changes detected
    """
    file_path = BASE_PATH / filename

    # Load existing data to compare
    existing = load_existing_data(filename)

    # Compare existing with new data
    if existing == data:
        print(f"  No changes detected in {filename}, skipping write")
        return False

    # Data has changed, save it
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

    print(f"  Saved changes to {filename}")
    return True


def update_chromium_versions():
    """Update Chromium versions (fetch last 10 per platform)."""
    print("Updating Chromium versions...")

    existing = load_existing_data("chromium_versions.json")
    if not existing:
        existing = {"by_major_version": {}, "platforms": {}}

    platforms = ["Windows", "Linux", "Mac", "Android", "iOS"]
    new_versions_count = 0

    for platform in platforms:
        url = f"https://chromiumdash.appspot.com/fetch_releases?channel=Stable&platform={platform}&num=10"

        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())

            for v in data:
                version = v.get("version", "")
                major = str(v.get("milestone", ""))

                if not version or not major:
                    continue

                # Add to by_major_version
                if major not in existing["by_major_version"]:
                    existing["by_major_version"][major] = []

                if version not in existing["by_major_version"][major]:
                    existing["by_major_version"][major].append(version)
                    new_versions_count += 1

            print(f"  {platform}: Checked {len(data)} versions")

        except Exception as e:
            print(f"  {platform}: Error - {e}")

    # Sort versions
    for major in existing["by_major_version"]:
        existing["by_major_version"][major] = sorted(
            list(set(existing["by_major_version"][major])),
            reverse=True
        )

    save_data("chromium_versions.json", existing)
    print(f"  Added {new_versions_count} new Chromium versions")


def update_chrome_versions():
    """Update Chrome versions (fetch last 10 per platform)."""
    print("\nUpdating Chrome versions...")

    existing = load_existing_data("chrome_versions.json")
    if not existing:
        existing = {"windows": {}, "macos": {}, "linux": {}}

    platforms = {
        "windows": ["win", "win64"],
        "macos": ["mac", "mac_arm64"],
        "linux": ["linux"]
    }

    new_versions_count = 0

    for os_name, platform_list in platforms.items():
        if os_name not in existing:
            existing[os_name] = {"all_versions": [], "by_major_version": {}}

        os_versions = set(existing[os_name].get("all_versions", []))

        for platform in platform_list:
            url = f"https://versionhistory.googleapis.com/v1/chrome/platforms/{platform}/channels/stable/versions?pageSize=1000"

            try:
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read().decode())

                for v_obj in data.get("versions", []):
                    version = v_obj.get("version", "")
                    if version and version != "unknown_version":
                        if version not in os_versions:
                            os_versions.add(version)
                            new_versions_count += 1

            except Exception as e:
                print(f"  {platform}: Error - {e}")

        # Update all_versions and by_major_version
        all_versions_list = sorted(list(os_versions), reverse=True)
        existing[os_name]["all_versions"] = all_versions_list[:100]

        # Rebuild by_major_version
        by_major = {}
        for version in all_versions_list:
            try:
                major = version.split('.')[0]
                if major not in by_major:
                    by_major[major] = []
                by_major[major].append(version)
            except (ValueError, IndexError):
                continue

        existing[os_name]["by_major_version"] = by_major

        print(f"  {os_name}: {len(os_versions)} total versions")

    save_data("chrome_versions.json", existing)
    print(f"  Added {new_versions_count} new Chrome versions")


def update_edge_versions():
    """Update Edge versions (parse from Microsoft docs)."""
    print("\nUpdating Edge versions...")

    existing = load_existing_data("edge_versions.json")
    if not existing:
        existing = {"windows": {}, "macos": {}, "linux": {}}

    # Fetch from current release notes only
    url = "https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-stable-channel"

    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')

        patterns = [
            r'Version\s+(\d{2,3}\.\d+\.\d+\.\d+)',
            r'\b(\d{2,3}\.\d+\.\d+\.\d+)\b',
        ]

        new_versions = set()
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                version = match.group(1)
                parts = version.split('.')
                if len(parts) == 4:
                    major = int(parts[0])
                    if 80 <= major <= 200:
                        new_versions.add(version)

        # Add to existing versions
        all_existing = set(existing.get("windows", {}).get("all_versions", []))
        added = 0

        for version in new_versions:
            if version not in all_existing:
                all_existing.add(version)
                added += 1

        # Update all platforms
        all_versions_list = sorted(list(all_existing), reverse=True)

        # Rebuild by_major_version
        by_major = {}
        for version in all_versions_list:
            try:
                major = version.split('.')[0]
                if major not in by_major:
                    by_major[major] = []
                by_major[major].append(version)
            except (ValueError, IndexError):
                continue

        for platform in ["windows", "macos", "linux"]:
            existing[platform] = {
                "all_versions": all_versions_list[:100],
                "by_major_version": by_major
            }

        save_data("edge_versions.json", existing)
        print(f"  Added {added} new Edge versions")

    except Exception as e:
        print(f"  Error: {e}")


def update_opera_versions():
    """Update Opera versions (parse from directory listing)."""
    print("\nUpdating Opera versions...")

    existing = load_existing_data("opera_versions.json")
    if not existing:
        existing = {"windows": {}, "macos": {}, "linux": {}}

    url = "https://get.opera.com/pub/opera/desktop/"

    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')

        pattern = r'<a href="([\d.]+)/">([\d.]+)/</a>'
        matches = re.finditer(pattern, content)

        new_versions = set()
        for match in matches:
            version = match.group(1)
            if version and version.count('.') == 3:
                new_versions.add(version)

        # Get last 10 versions only
        new_versions_list = sorted(list(new_versions), reverse=True)[:10]

        # Add to existing versions
        all_existing = set(existing.get("windows", {}).get("all_versions", []))
        added = 0

        for version in new_versions_list:
            if version not in all_existing:
                all_existing.add(version)
                added += 1

        # Update all platforms
        all_versions_list = sorted(list(all_existing), reverse=True)

        # Rebuild by_major_version
        by_major = {}
        for version in all_versions_list:
            try:
                major = version.split('.')[0]
                if major not in by_major:
                    by_major[major] = []
                by_major[major].append(version)
            except (ValueError, IndexError):
                continue

        for platform in ["windows", "macos", "linux"]:
            existing[platform] = {
                "all_versions": all_versions_list[:100],
                "by_major_version": by_major
            }

        save_data("opera_versions.json", existing)
        print(f"  Added {added} new Opera versions")

    except Exception as e:
        print(f"  Error: {e}")


def main():
    """Run all update tasks."""
    print("=== Browser Version Update Script ===\n")

    update_chromium_versions()
    update_chrome_versions()
    update_edge_versions()
    update_opera_versions()

    print("\n✓ All browser versions updated!")


if __name__ == "__main__":
    main()

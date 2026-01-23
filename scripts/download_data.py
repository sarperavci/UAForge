#!/usr/bin/env python3
import json
import urllib.request
import tarfile
import io
from pathlib import Path
import sys


DATA_DIR = Path(__file__).parent.parent / "uaforge" / "data"
GITHUB_API_URL = "https://api.github.com/repos/sarperavci/UAForge/releases"

LARGE_DATA_FILES = [
    "chrome_versions.json",
    "chromium_versions.json",
    "edge_versions.json",
    "opera_versions.json",
]

SMALL_DATA_FILES = [
    "device_models.json",
    "market_share.json",
    "os_distribution.json",
]


def get_latest_data_release():
    """Get the latest data release tag from GitHub."""
    try:
        req = urllib.request.Request(GITHUB_API_URL)
        req.add_header('Accept', 'application/vnd.github.v3+json')

        with urllib.request.urlopen(req, timeout=10) as response:
            releases = json.loads(response.read().decode())

        # Find the latest data release (tagged with 'data-')
        for release in releases:
            tag = release.get('tag_name', '')
            if tag.startswith('data-'):
                return release

        return None
    except Exception as e:
        print(f"Error fetching releases: {e}")
        return None


def download_data_archive():
    """Download and extract the browser-data.tar.gz archive from latest release."""
    print("Fetching latest browser data release...")

    release = get_latest_data_release()
    if not release:
        print("Warning: No data release found. Using fallback to latest tag...")
        # Fallback to latest/download
        archive_url = "https://github.com/sarperavci/UAForge/releases/latest/download/browser-data.tar.gz"
    else:
        # Get download URL from release assets
        assets = release.get('assets', [])
        archive_asset = next((a for a in assets if a['name'] == 'browser-data.tar.gz'), None)

        if not archive_asset:
            print("Error: browser-data.tar.gz not found in release assets")
            return False

        archive_url = archive_asset['browser_download_url']
        print(f"Found release: {release['tag_name']}")

    print(f"Downloading browser data archive...", end=" ")

    try:
        with urllib.request.urlopen(archive_url, timeout=30) as response:
            archive_data = response.read()

        print("✓")
        print("Extracting data files...", end=" ")

        # Extract tar.gz
        with tarfile.open(fileobj=io.BytesIO(archive_data), mode='r:gz') as tar:
            tar.extractall(path=DATA_DIR)

        print("✓")
        return True

    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("✗ (No release found)")
            print("\nℹ️  No data release exists yet.")
            print("   Large data files will be generated on first use.")
            return False
        else:
            print(f"✗ (HTTP {e.code})")
            return False
    except Exception as e:
        print(f"✗ ({e})")
        return False


def check_data_exists():
    """Check if all required data files exist."""
    missing = []

    for filename in LARGE_DATA_FILES:
        if not (DATA_DIR / filename).exists():
            missing.append(filename)

    for filename in SMALL_DATA_FILES:
        if not (DATA_DIR / filename).exists():
            missing.append(filename)

    return len(missing) == 0, missing


def download_all_data():
    """Download all required data files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Check what's missing
    all_exists, missing = check_data_exists()

    if all_exists:
        print("All data files already exist.")
        return True

    print(f"Missing data files: {', '.join(missing)}")

    # Download large files from release
    needs_large = any(f in LARGE_DATA_FILES for f in missing)

    if needs_large:
        if not download_data_archive():
            print("\nWarning: Could not download data archive.")
            print("The library will work with limited browser version data.")
            print("Run 'python scripts/update_browser_versions.py' to generate data locally.")
            return False

    # Check again
    all_exists, still_missing = check_data_exists()

    if still_missing:
        print(f"\nWarning: Some files are still missing: {', '.join(still_missing)}")
        return False

    print("\n✓ All data files are ready!")
    return True


if __name__ == "__main__":
    success = download_all_data()
    sys.exit(0 if success else 1)

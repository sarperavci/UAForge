"""
Setup script for UAForge with post-install data download.
"""

import os
import sys
from pathlib import Path
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        install.run(self)
        self._download_data()

    def _download_data(self):
        """Download browser data files after installation."""
        print("\n" + "=" * 60)
        print("UAForge: Downloading browser data files...")
        print("=" * 60 + "\n")

        # Import and run download script
        try:
            # Get the installation directory
            install_lib = self.install_lib
            data_dir = Path(install_lib) / "uaforge" / "data"

            # Download the data
            import json
            import urllib.request
            import tarfile
            import io

            GITHUB_API_URL = "https://api.github.com/repos/sarperavci/UAForge/releases"

            # Check if files already exist
            large_files = [
                "chrome_versions.json",
                "chromium_versions.json",
                "edge_versions.json",
                "opera_versions.json",
            ]

            missing = [f for f in large_files if not (data_dir / f).exists()]

            if not missing:
                print("✓ All data files already present\n")
                return

            print(f"Missing: {', '.join(missing)}")
            print("Fetching from GitHub releases...")

            # Get latest data release
            req = urllib.request.Request(GITHUB_API_URL)
            req.add_header('Accept', 'application/vnd.github.v3+json')

            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    releases = json.loads(response.read().decode())

                # Find latest data release
                data_release = None
                for release in releases:
                    if release.get('tag_name', '').startswith('data-'):
                        data_release = release
                        break

                if data_release:
                    assets = data_release.get('assets', [])
                    archive = next((a for a in assets if a['name'] == 'browser-data.tar.gz'), None)

                    if archive:
                        print(f"Found release: {data_release['tag_name']}")
                        print("Downloading browser-data.tar.gz...", end=" ", flush=True)

                        with urllib.request.urlopen(archive['browser_download_url'], timeout=30) as response:
                            archive_data = response.read()

                        print("✓")
                        print("Extracting...", end=" ", flush=True)

                        with tarfile.open(fileobj=io.BytesIO(archive_data), mode='r:gz') as tar:
                            tar.extractall(path=data_dir)

                        print("✓")
                        print("\n✓ Browser data downloaded successfully!")
                        print("=" * 60 + "\n")
                        return

            except Exception as e:
                print(f"\nWarning: Could not download from releases: {e}")

            # If we get here, download failed
            print("\nℹ️  Could not download browser data files.")
            print("   The library will work with limited version data.")
            print("   You can download manually later:")
            print("   $ python -c 'from uaforge.data.loader import DataLoader; DataLoader()'")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"\nWarning: Error during data download: {e}")
            print("You can download data manually later with:")
            print("  python -c 'from uaforge.data.loader import DataLoader; DataLoader()'")
            print("=" * 60 + "\n")


class PostDevelopCommand(develop):
    """Post-installation for development mode."""

    def run(self):
        develop.run(self)
        # In development mode, don't auto-download (developer has the files)
        print("\n" + "=" * 60)
        print("UAForge: Installed in development mode")
        print("Data files are already present in source directory")
        print("=" * 60 + "\n")


# Run setup
if __name__ == "__main__":
    setup(
        cmdclass={
            'install': PostInstallCommand,
            'develop': PostDevelopCommand,
        },
    )

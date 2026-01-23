# Data Update Scripts

This directory contains scripts for updating the data files used by UAForge.

## Initial Data Fetching

### `fetch_chromium_versions.py`

Fetches stable Chromium versions from Chromium Dash API for all platforms.

**Usage:**
```bash
python scripts/fetch_chromium_versions.py
```

**What it does:**
- Fetches up to 1000 stable Chromium versions per platform (Windows, Linux, Mac, Android, iOS)
- Organizes versions by major version number
- Creates `uaforge/data/chromium_versions.json` with minified JSON

**API Source:**
- Chromium Dash API: https://chromiumdash.appspot.com/fetch_releases
- Fetches from stable channel only

### `fetch_chrome_versions.py`

Fetches stable Chrome versions from Google's VersionHistory API.

**Usage:**
```bash
python scripts/fetch_chrome_versions.py
```

**What it does:**
- Fetches stable Chrome versions for Windows, macOS, and Linux
- Stores last 100 versions per platform
- Groups by major version
- Creates `uaforge/data/chrome_versions.json` with minified JSON

**API Source:**
- Google Chrome VersionHistory API: https://versionhistory.googleapis.com/v1

### `fetch_edge_versions.py`

Fetches Microsoft Edge versions by parsing release notes from Microsoft Learn.

**Usage:**
```bash
python scripts/fetch_edge_versions.py
```

**What it does:**
- Parses current and archived Edge release notes
- Extracts version numbers using regex
- Creates `uaforge/data/edge_versions.json` with minified JSON

**Sources:**
- Current: https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-stable-channel
- Archive: https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-archive-stable-channel

### `fetch_opera_versions.py`

Fetches Opera versions from Opera's directory listing.

**Usage:**
```bash
python scripts/fetch_opera_versions.py
```

**What it does:**
- Parses Opera's public directory listing
- Extracts all available Opera versions
- Creates `uaforge/data/opera_versions.json` with minified JSON

**Source:**
- Opera directory: https://get.opera.com/pub/opera/desktop/

**Note:** Opera major version + 16 = corresponding Chromium major version

## Periodic Updates

### `update_browser_versions.py`

Updates all browser version data by fetching only recent versions and appending to existing data.

**Usage:**
```bash
python scripts/update_browser_versions.py
```

**What it does:**
- Fetches latest 10 versions per platform (instead of all versions)
- Appends new versions to existing data (doesn't overwrite)
- Updates: Chromium, Chrome, Edge, and Opera
- Saves as minified JSON

**When to run:**
- Weekly or monthly via cron/GitHub Actions
- After major browser releases
- Before deploying updates

## Version Mapping

### Browser to Chromium Mapping

- **Chrome**: Uses Chrome version directly
- **Edge**: Same major version as Chromium (e.g., Edge 144 = Chromium 144)
- **Opera**: Opera major + 16 = Chromium major (e.g., Opera 122 = Chromium 138)
- **Firefox**: Independent versioning
- **Safari**: Independent versioning

## Output Format

All version files use minified JSON with this structure:

```json
{
  "windows": {
    "all_versions": ["144.0.7559.96", "143.0.7499.192", ...],
    "by_major_version": {
      "144": ["144.0.7559.96", "144.0.7559.59", ...],
      "143": ["143.0.7499.192", "143.0.7499.169", ...]
    }
  },
  "macos": { ... },
  "linux": { ... }
}
```

## Automation

Recommended automation schedule:

```yaml
# GitHub Actions example
schedule:
  - cron: '0 0 * * 0'  # Weekly on Sunday
```

```bash
# Crontab example
0 0 * * 0 cd /path/to/ua-gen && python scripts/update_browser_versions.py
```

#!/usr/bin/env python3
"""
GSMArena Device Specifications Scraper

Fetches device specifications from GSMArena including:
- Model codes (SM-G530H, Pixel 9, etc.)
- Launch Android version
- Maximum supported Android version
- Popularity metrics (hits/daily interest)

Uses BeautifulSoup for HTML parsing with rate limiting and retry logic.
"""

import json
import re
import time
import random
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from html.parser import HTMLParser
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Android version to API level mapping
ANDROID_VERSION_TO_API = {
    "1.0": 1, "1.1": 2, "1.5": 3, "1.6": 4, "2.0": 5, "2.0.1": 6, "2.1": 7,
    "2.2": 8, "2.3": 9, "2.3.3": 10, "3.0": 11, "3.1": 12, "3.2": 13,
    "4.0": 14, "4.0.3": 15, "4.1": 16, "4.2": 17, "4.3": 18, "4.4": 19,
    "5.0": 21, "5.1": 22, "6.0": 23, "7.0": 24, "7.1": 25, "8.0": 26,
    "8.1": 27, "9": 28, "9.0": 28, "10": 29, "11": 30, "12": 31, "12L": 32,
    "13": 33, "14": 34, "15": 35, "16": 36
}

# Reverse mapping
API_TO_ANDROID_VERSION = {v: k for k, v in ANDROID_VERSION_TO_API.items()}


@dataclass
class DeviceSpec:
    """Device specification data."""
    model_code: str  # e.g., "SM-G530H", "Pixel 9"
    brand: str  # e.g., "samsung", "google"
    name: str  # Human-readable name
    min_android_api: int  # Launch Android API level
    max_android_api: int  # Maximum supported Android API level
    popularity: float  # Normalized popularity score (0-1)
    year: int  # Release year


class GSMArenaHTMLParser(HTMLParser):
    """Simple HTML parser for GSMArena pages."""

    def __init__(self):
        super().__init__()
        self.specs = {}
        self.current_spec = None
        self.in_spec_value = False
        self.data_buffer = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "td" and attrs_dict.get("data-spec"):
            self.current_spec = attrs_dict["data-spec"]
            self.in_spec_value = True
            self.data_buffer = []

    def handle_endtag(self, tag):
        if tag == "td" and self.in_spec_value:
            if self.current_spec and self.data_buffer:
                self.specs[self.current_spec] = " ".join(self.data_buffer).strip()
            self.in_spec_value = False
            self.current_spec = None

    def handle_data(self, data):
        if self.in_spec_value:
            self.data_buffer.append(data.strip())


def parse_android_version(os_string: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse Android version string to extract min and max API levels.

    Examples:
        "Android 4.4.2 (KitKat)" -> (19, 19)
        "Android 11, upgradable to Android 14" -> (30, 34)
        "Android 10, One UI 2.1" -> (29, 29)

    Returns:
        Tuple of (min_api, max_api) or (None, None) if parsing fails
    """
    if not os_string or "Android" not in os_string:
        return None, None

    # Find all Android version numbers
    versions = re.findall(r'Android (\d+(?:\.\d+)*)', os_string)

    if not versions:
        return None, None

    # Convert versions to API levels
    api_levels = []
    for v in versions:
        # Normalize version (e.g., "14" -> "14", "4.4.2" -> "4.4")
        parts = v.split('.')
        if len(parts) >= 2:
            normalized = f"{parts[0]}.{parts[1]}"
        else:
            normalized = parts[0]

        api = ANDROID_VERSION_TO_API.get(normalized) or ANDROID_VERSION_TO_API.get(parts[0])
        if api:
            api_levels.append(api)

    if not api_levels:
        return None, None

    return min(api_levels), max(api_levels)


def parse_release_year(announced: str) -> Optional[int]:
    """Parse release year from announced string."""
    if not announced:
        return None

    match = re.search(r'20\d{2}', announced)
    return int(match.group()) if match else None


def fetch_page(url: str, retries: int = 3, delay: float = 2.0) -> Optional[str]:
    """
    Fetch a page with retry logic and rate limiting.

    Args:
        url: URL to fetch
        retries: Number of retry attempts
        delay: Base delay between requests (with jitter)

    Returns:
        HTML content or None if failed
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    for attempt in range(retries):
        try:
            # Add jitter to delay
            time.sleep(delay + random.uniform(0, 1))

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read().decode('utf-8')

        except urllib.error.HTTPError as e:
            if e.code == 429:  # Rate limited
                wait_time = (attempt + 1) * 10
                print(f"  Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            elif e.code == 404:
                return None
            else:
                print(f"  HTTP error {e.code} for {url}")

        except Exception as e:
            print(f"  Error fetching {url}: {e}")

        if attempt < retries - 1:
            time.sleep(delay * (attempt + 1))

    return None


def extract_model_codes(html: str, brand: str) -> List[str]:
    """
    Extract model codes from device page HTML.

    Different brands use different model code patterns:
    - Samsung: SM-G530H, SM-A546B
    - Google: Pixel 9, Pixel 8a
    - Xiaomi: 2201116SG, M2012K11AC
    - OPPO: CPH2195, PEEM00
    """
    model_codes = []

    # Samsung model codes
    samsung_matches = re.findall(r'SM-[A-Z]\d{3,4}[A-Z0-9]*', html)
    model_codes.extend(samsung_matches)

    # Xiaomi model codes
    xiaomi_matches = re.findall(r'[A-Z0-9]{8,12}(?:SG|IN|EU|CN)', html)
    model_codes.extend(xiaomi_matches)

    # OPPO/Realme model codes
    oppo_matches = re.findall(r'CPH\d{4}|PEEM\d{2}|PEGM\d{2}', html)
    model_codes.extend(oppo_matches)

    return list(set(model_codes))


def parse_device_list_page(html: str) -> List[Dict]:
    """
    Parse device list page to extract device URLs and names.

    Returns list of dicts with 'url', 'name', and 'img' keys.
    """
    devices = []

    # Pattern for device links in GSMArena
    # <a href="samsung_galaxy_s25_ultra-13234.php">Samsung Galaxy S25 Ultra</a>
    pattern = r'<a href="([a-z0-9_-]+\.php)"[^>]*>\s*<img[^>]+>\s*<span[^>]*>([^<]+)</span>'

    for match in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
        devices.append({
            'url': match.group(1),
            'name': match.group(2).strip()
        })

    return devices


def scrape_device_specs(device_url: str, brand: str) -> Optional[DeviceSpec]:
    """
    Scrape specifications for a single device.

    Args:
        device_url: Relative URL to device page
        brand: Brand name

    Returns:
        DeviceSpec or None if scraping failed
    """
    full_url = f"https://www.gsmarena.com/{device_url}"
    html = fetch_page(full_url)

    if not html:
        return None

    parser = GSMArenaHTMLParser()
    try:
        parser.feed(html)
    except Exception:
        return None

    specs = parser.specs

    # Extract OS information
    os_string = specs.get("os", "")
    min_api, max_api = parse_android_version(os_string)

    if min_api is None:
        return None  # Not an Android device or couldn't parse

    # Extract year
    announced = specs.get("released-hl", "") or specs.get("year", "")
    year = parse_release_year(announced)

    # Extract model codes
    models_string = specs.get("models", "")
    model_codes = extract_model_codes(models_string + " " + html[:5000], brand)

    # Extract name
    name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    name = name_match.group(1).strip() if name_match else device_url.replace('.php', '')

    # Get primary model code or use name
    model_code = model_codes[0] if model_codes else name.split()[-1]

    # Extract popularity (hits counter)
    popularity_match = re.search(r'(\d+) hits', html)
    popularity = int(popularity_match.group(1)) if popularity_match else 0

    return DeviceSpec(
        model_code=model_code,
        brand=brand,
        name=name,
        min_android_api=min_api,
        max_android_api=max_api,
        popularity=popularity / 1_000_000,  # Normalize to millions
        year=year or 2020
    )


def scrape_brand_devices(brand: str, brand_url: str, max_devices: int = 100) -> List[DeviceSpec]:
    """
    Scrape device specifications for a brand.

    Args:
        brand: Brand identifier
        brand_url: URL to brand's device listing
        max_devices: Maximum number of devices to scrape

    Returns:
        List of DeviceSpec objects
    """
    print(f"\nScraping {brand}...")

    html = fetch_page(brand_url)
    if not html:
        print(f"  Failed to fetch brand page")
        return []

    devices = parse_device_list_page(html)
    print(f"  Found {len(devices)} devices")

    specs = []
    for i, device in enumerate(devices[:max_devices]):
        print(f"  [{i+1}/{min(len(devices), max_devices)}] {device['name']}")

        spec = scrape_device_specs(device['url'], brand)
        if spec:
            specs.append(spec)
            print(f"    -> {spec.model_code} (Android API {spec.min_android_api}-{spec.max_android_api})")

        # Respect rate limiting
        time.sleep(1.5)

    return specs


def generate_estimated_specs() -> Dict[str, List[Dict]]:
    """
    Generate estimated Android version specs for existing devices in device_models.json.

    This uses heuristics based on device model patterns and release dates
    to estimate Android version support without scraping.
    """
    # Load existing device models
    data_path = Path(__file__).parent.parent / "uaforge" / "data" / "device_models.json"
    with open(data_path, 'r') as f:
        existing_models = json.load(f)

    result = {}

    # Samsung model generation mapping (based on model code patterns)
    # More detailed mapping based on actual Samsung model codes
    samsung_generation_map = {
        # SM-G1XX: Galaxy Pocket/Young (2012-2014) - Android 4.0-4.4 (API 14-19)
        "SM-G110": (14, 19, 2014),
        "SM-G130": (14, 19, 2014),
        "SM-G150": (21, 23, 2016),
        "SM-G155": (23, 25, 2017),
        "SM-G160": (23, 25, 2016),

        # SM-G3XX: Galaxy Core/Ace/Win (2013-2015) - Android 4.1-5.1 (API 16-22)
        "SM-G310": (16, 19, 2014),
        "SM-G313": (19, 21, 2014),
        "SM-G316": (19, 21, 2014),
        "SM-G318": (19, 22, 2015),
        "SM-G350": (19, 22, 2014),
        "SM-G355": (19, 22, 2014),
        "SM-G357": (19, 22, 2014),
        "SM-G360": (19, 23, 2015),  # Galaxy Core Prime
        "SM-G361": (21, 23, 2015),
        "SM-G368": (21, 23, 2015),
        "SM-G381": (19, 22, 2014),
        "SM-G386": (19, 21, 2014),
        "SM-G388": (21, 23, 2015),
        "SM-G389": (23, 26, 2016),
        "SM-G390": (24, 28, 2017),
        "SM-G398": (26, 29, 2019),

        # SM-G5XX: Galaxy J2/Grand Prime (2014-2018) - Android 4.4-8.0 (API 19-26)
        "SM-G510": (19, 22, 2014),
        "SM-G525": (29, 32, 2021),  # Galaxy Xcover 5
        "SM-G530": (19, 23, 2014),  # Galaxy Grand Prime - key device!
        "SM-G531": (21, 23, 2015),
        "SM-G532": (23, 25, 2016),
        "SM-G550": (23, 26, 2016),
        "SM-G551": (23, 26, 2016),
        "SM-G570": (24, 27, 2017),  # Galaxy J5 Prime

        # SM-G6XX: Galaxy J7 Prime/On series (2016-2019) - Android 6.0-10 (API 23-29)
        "SM-G600": (23, 26, 2016),
        "SM-G610": (23, 28, 2016),  # Galaxy J7 Prime
        "SM-G611": (24, 28, 2017),
        "SM-G615": (24, 28, 2017),
        "SM-G620": (24, 28, 2017),

        # SM-G7XX: Galaxy A/Xcover (2014-2020) - Android 5.0-11 (API 21-30)
        "SM-G710": (19, 22, 2014),
        "SM-G715": (28, 31, 2020),  # Galaxy Xcover Pro
        "SM-G720": (21, 25, 2015),
        "SM-G730": (19, 21, 2013),
        "SM-G750": (19, 22, 2014),
        "SM-G770": (29, 33, 2020),  # Galaxy S10 Lite
        "SM-G780": (29, 34, 2020),  # Galaxy S20 FE
        "SM-G781": (29, 34, 2020),

        # SM-G8XX: Galaxy S5/S6/A8 series (2014-2020) - Android 4.4-11 (API 19-30)
        "SM-G800": (19, 23, 2014),  # Galaxy S5 Mini
        "SM-G820": (21, 24, 2015),
        "SM-G850": (19, 23, 2014),  # Galaxy Alpha
        "SM-G860": (19, 23, 2014),
        "SM-G870": (19, 23, 2014),  # Galaxy S5 Active
        "SM-G875": (23, 28, 2016),
        "SM-G885": (26, 30, 2018),  # Galaxy A8 Star
        "SM-G887": (26, 30, 2018),  # Galaxy A8s
        "SM-G888": (24, 26, 2017),
        "SM-G889": (26, 29, 2018),
        "SM-G890": (21, 24, 2015),  # Galaxy S6 Active
        "SM-G891": (23, 28, 2016),  # Galaxy S7 Active
        "SM-G892": (24, 28, 2017),  # Galaxy S8 Active

        # SM-G9XXX: Galaxy S series flagship (2014-2024) - detailed mapping
        "SM-G900": (19, 23, 2014),  # Galaxy S5
        "SM-G901": (21, 23, 2014),
        "SM-G903": (21, 25, 2015),  # Galaxy S5 Neo
        "SM-G906": (19, 23, 2014),
        "SM-G909": (19, 22, 2014),
        "SM-G910": (19, 23, 2014),
        "SM-G919": (21, 23, 2015),
        "SM-G920": (21, 26, 2015),  # Galaxy S6
        "SM-G925": (21, 26, 2015),  # Galaxy S6 Edge
        "SM-G928": (21, 26, 2015),  # Galaxy S6 Edge+
        "SM-G929": (21, 26, 2015),
        "SM-G930": (23, 28, 2016),  # Galaxy S7
        "SM-G935": (23, 28, 2016),  # Galaxy S7 Edge
        "SM-G950": (24, 30, 2017),  # Galaxy S8
        "SM-G955": (24, 30, 2017),  # Galaxy S8+
        "SM-G960": (26, 30, 2018),  # Galaxy S9
        "SM-G965": (26, 30, 2018),  # Galaxy S9+
        "SM-G970": (28, 31, 2019),  # Galaxy S10e
        "SM-G973": (28, 31, 2019),  # Galaxy S10
        "SM-G975": (28, 31, 2019),  # Galaxy S10+
        "SM-G977": (28, 31, 2019),  # Galaxy S10 5G
        "SM-G980": (29, 33, 2020),  # Galaxy S20
        "SM-G981": (29, 33, 2020),  # Galaxy S20 5G
        "SM-G985": (29, 33, 2020),  # Galaxy S20+
        "SM-G986": (29, 33, 2020),  # Galaxy S20+ 5G
        "SM-G988": (29, 33, 2020),  # Galaxy S20 Ultra
        "SM-G990": (30, 34, 2021),  # Galaxy S21 FE
        "SM-G991": (30, 34, 2021),  # Galaxy S21
        "SM-G996": (30, 34, 2021),  # Galaxy S21+
        "SM-G998": (30, 34, 2021),  # Galaxy S21 Ultra
    }

    samsung_devices = []
    for model in existing_models.get("samsung", []):
        min_api, max_api, year = (28, 34, 2020)  # Default for unknown models

        # Try to match by progressively shorter prefixes (from longest to shortest)
        matched = False
        for prefix_len in range(min(len(model), 7), 3, -1):
            prefix = model[:prefix_len]
            if prefix in samsung_generation_map:
                min_api, max_api, year = samsung_generation_map[prefix]
                matched = True
                break

        # If no match, try pattern-based detection as fallback
        if not matched:
            # SM-GXXX pattern - extract the 3-digit model number
            import re
            match = re.match(r'SM-G(\d{3,4})', model)
            if match:
                model_num = int(match.group(1))
                if model_num < 200:  # SM-G1XX
                    min_api, max_api, year = (14, 19, 2013)
                elif model_num < 400:  # SM-G2XX, SM-G3XX
                    min_api, max_api, year = (16, 22, 2014)
                elif model_num < 600:  # SM-G4XX, SM-G5XX
                    min_api, max_api, year = (19, 24, 2015)
                elif model_num < 700:  # SM-G6XX
                    min_api, max_api, year = (23, 28, 2017)
                elif model_num < 800:  # SM-G7XX
                    min_api, max_api, year = (24, 30, 2018)
                elif model_num < 900:  # SM-G8XX
                    min_api, max_api, year = (21, 29, 2016)
                elif model_num < 950:  # SM-G90X, SM-G91X, SM-G92X, SM-G93X, SM-G94X
                    # Older S series (S5-S7)
                    min_api, max_api, year = (21, 28, 2016)
                elif model_num < 970:  # SM-G95X, SM-G96X
                    # S8/S9 era
                    min_api, max_api, year = (25, 30, 2018)
                elif model_num < 990:  # SM-G97X, SM-G98X
                    # S10/S20 era
                    min_api, max_api, year = (28, 33, 2019)
                else:  # SM-G99X
                    # S21+ era
                    min_api, max_api, year = (30, 34, 2021)

        # Adjust popularity based on device age - newer devices more popular
        base_popularity = random.uniform(0.001, 0.05)
        if year >= 2023:
            popularity = base_popularity * 3
        elif year >= 2021:
            popularity = base_popularity * 2
        elif year >= 2019:
            popularity = base_popularity * 1.5
        else:
            popularity = base_popularity * 0.5

        samsung_devices.append({
            "model_code": model,
            "brand": "samsung",
            "name": model,
            "min_android_api": min_api,
            "max_android_api": max_api,
            "popularity": popularity,
            "year": year
        })

    result["samsung"] = samsung_devices

    # Google Pixel mapping
    pixel_api_map = {
        "Pixel 2": (26, 30, 2017),     # Launched 8.0, ended at 11
        "Pixel 2 XL": (26, 30, 2017),
        "Pixel 3": (28, 31, 2018),     # Launched 9, ended at 12
        "Pixel 3 XL": (28, 31, 2018),
        "Pixel 3a": (28, 31, 2019),
        "Pixel 3a XL": (28, 31, 2019),
        "Pixel 4": (29, 32, 2019),     # Launched 10, ended at 13
        "Pixel 4 XL": (29, 32, 2019),
        "Pixel 4a": (30, 33, 2020),    # Launched 11, ended at 14
        "Pixel 4a (5G)": (30, 33, 2020),
        "Pixel 5": (30, 33, 2020),
        "Pixel 5a": (30, 34, 2021),
        "Pixel 6": (31, 35, 2021),     # Launched 12, through 15
        "Pixel 6 Pro": (31, 35, 2021),
        "Pixel 6a": (31, 35, 2022),
        "Pixel 7": (33, 35, 2022),     # Launched 13, through 15+
        "Pixel 7 Pro": (33, 35, 2022),
        "Pixel 7a": (33, 35, 2023),
        "Pixel 8": (34, 35, 2023),     # Launched 14
        "Pixel 8 Pro": (34, 35, 2023),
        "Pixel 8a": (34, 35, 2024),
        "Pixel 9": (35, 35, 2024),     # Launched 15
        "Pixel 9 Pro": (35, 35, 2024),
        "Pixel 9a": (35, 35, 2025),
    }

    pixel_devices = []
    for model in existing_models.get("google_pixel", []):
        min_api, max_api, year = pixel_api_map.get(model, (33, 35, 2023))

        # Newer Pixels are more popular
        popularity = 0.2 if "9" in model else (0.15 if "8" in model else 0.1)

        pixel_devices.append({
            "model_code": model,
            "brand": "google",
            "name": f"Google {model}",
            "min_android_api": min_api,
            "max_android_api": max_api,
            "popularity": popularity,
            "year": year
        })

    result["google_pixel"] = pixel_devices

    # OPPO/Realme - Most are recent devices
    oppo_devices = []
    for model in existing_models.get("oppo_realme_generic", []):
        # CPH codes: first 2 digits after CPH indicate year roughly
        # CPH19XX = 2019, CPH20XX = 2020, CPH21XX = 2021, etc.
        if model.startswith("CPH"):
            try:
                year_hint = int(model[3:5])
                year = 2000 + year_hint if year_hint < 50 else 1900 + year_hint
                year = max(2018, min(2025, year))  # Clamp to reasonable range
            except ValueError:
                year = 2021
        else:
            year = 2021

        # Map year to Android versions
        year_to_api = {
            2018: (26, 29), 2019: (28, 30), 2020: (29, 31),
            2021: (30, 33), 2022: (31, 34), 2023: (33, 34),
            2024: (34, 35), 2025: (35, 35)
        }
        min_api, max_api = year_to_api.get(year, (30, 34))

        oppo_devices.append({
            "model_code": model,
            "brand": "oppo",
            "name": model,
            "min_android_api": min_api,
            "max_android_api": max_api,
            "popularity": random.uniform(0.01, 0.08),
            "year": year
        })

    result["oppo_realme_generic"] = oppo_devices

    # Comprehensive manual overrides for Xiaomi devices (accurate data from GSMArena)
    # Format: device_name: (min_android_api, max_android_api, year)
    xiaomi_manual_overrides = {
        # === Redmi K Series (CRITICAL - these need to be accurate) ===
        "Redmi K20": (28, 29, 2019),  # Android 9, upgradable to Android 10 ONLY
        "Redmi K20 Pro": (28, 30, 2019),  # Android 9, upgradable to Android 11
        "Redmi K20 Pro Premium Edition": (28, 30, 2019),
        "Redmi K30 4G": (29, 31, 2019),  # Android 10, upgradable to Android 12
        "Redmi K30 5G": (29, 31, 2020),
        "Redmi K30 Pro Zoom": (29, 31, 2020),
        "Redmi K30 Pro Zoom Edition": (29, 31, 2020),
        "Redmi K30 Ultra": (29, 31, 2020),
        "Redmi K30i 5G": (29, 31, 2020),
        "Redmi K30S Ultra": (29, 31, 2020),
        "Redmi K40": (30, 33, 2021),  # Android 11, upgradable to Android 14
        "Redmi K40 Gaming": (30, 32, 2021),
        "Redmi K40 Pro": (30, 33, 2021),
        "Redmi K40 Pro+": (30, 33, 2021),
        "Redmi K40S": (31, 33, 2022),
        "Redmi K50": (31, 34, 2022),  # Android 12, upgradable to Android 14
        "Redmi K50 Pro": (31, 34, 2022),
        "Redmi K50 Ultra": (31, 34, 2022),
        "Redmi K50G": (31, 34, 2022),
        "Redmi K50i": (31, 33, 2022),
        "Redmi K60": (33, 35, 2023),  # Android 13, upgradable to Android 14+
        "Redmi K60 Pro": (33, 35, 2023),
        "Redmi K60 Ultra": (33, 35, 2023),
        "Redmi K60E": (33, 34, 2023),
        "Redmi K70": (34, 35, 2024),  # Android 14
        "Redmi K70 Pro": (34, 35, 2024),
        "Redmi K70 Ultra": (34, 35, 2024),
        "Redmi K70E": (34, 35, 2024),
        "Redmi K80 Pro": (35, 35, 2024),  # Android 15

        # === Redmi Y series (budget, limited updates) ===
        "Redmi Y1 Lite": (24, 25, 2017),  # Android 7.1 only
        "Redmi Y1": (24, 25, 2017),

        # === Older Redmi devices ===
        "Redmi 1": (19, 19, 2014),  # Android 4.4 only
        "Redmi 1S": (19, 19, 2014),
        "Redmi 2": (19, 22, 2015),  # Android 4.4 to 5.1
        "Redmi 2 Pro": (19, 22, 2015),
        "Redmi 2A": (19, 22, 2015),
        "Redmi 3": (21, 23, 2016),  # Android 5.1 to 6.0
        "Redmi 4 Prime": (23, 25, 2016),
        "Redmi 5": (24, 26, 2017),
        "Redmi 5 Plus": (24, 27, 2017),
        "Redmi 6 Pro Extreme": (26, 28, 2018),
        "Redmi 7A": (28, 29, 2019),
        "Redmi 8": (28, 30, 2019),
        "Redmi 8A": (28, 29, 2019),
        "Redmi 9": (29, 30, 2020),  # Android 10
        "Redmi 9 Power": (29, 31, 2020),
        "Redmi 9 Prime": (29, 31, 2020),
        "Redmi 9A": (29, 30, 2020),
        "Redmi 9AT": (29, 30, 2020),
        "Redmi 9C": (29, 30, 2020),
        "Redmi 9C NFC": (29, 30, 2020),
        "Redmi 9i": (29, 30, 2020),
        "Redmi 9i Sport": (30, 31, 2021),
        "Redmi 9T": (29, 31, 2021),
        "Redmi 9T NFC": (29, 31, 2021),
        "Redmi 10": (30, 32, 2021),  # Android 11, upgradable to 13
        "Redmi 10 (2022)": (30, 32, 2022),
        "Redmi 10 5G": (30, 32, 2022),
        "Redmi 10 Power": (30, 32, 2022),
        "Redmi 10 Prime": (30, 32, 2021),
        "Redmi 10 Prime (2022)": (30, 32, 2022),
        "Redmi 10 Prime+ 5G": (30, 32, 2022),
        "Redmi 10A": (30, 31, 2022),
        "Redmi 10C": (30, 32, 2022),
        "Redmi 10X": (29, 31, 2020),
        "Redmi 10X Pro": (29, 31, 2020),
        "Redmi 11 Prime": (31, 33, 2022),
        "Redmi 12": (33, 34, 2023),  # Android 13
        "Redmi 12 5G": (33, 34, 2023),
        "Redmi 12C": (31, 33, 2023),
        "Redmi 13": (34, 35, 2024),
        "Redmi 13 5G": (33, 34, 2024),
        "Redmi 13C": (33, 34, 2023),
        "Redmi 13C 5G": (33, 34, 2024),
        "Redmi 14C": (34, 35, 2024),
        "Redmi Go": (28, 28, 2019),  # Android Go edition

        # === Redmi Note Series ===
        "Redmi Note": (19, 21, 2014),
        "Redmi Note 3": (21, 23, 2016),
        "Redmi Note 5A Lite": (24, 25, 2017),
        "Redmi Note 5A Prime": (24, 26, 2017),
        "Redmi Note 7": (28, 29, 2019),  # Android 9, upgradable to 10
        "Redmi Note 7 Pro": (28, 29, 2019),
        "Redmi Note 7S": (28, 29, 2019),
        "Redmi Note 8": (28, 30, 2019),  # Android 9, upgradable to 11
        "Redmi Note 8 (2021)": (30, 31, 2021),
        "Redmi Note 8 Pro": (28, 30, 2019),
        "Redmi Note 8T": (28, 30, 2019),
        "Redmi Note 9": (29, 31, 2020),  # Android 10, upgradable to 12
        "Redmi Note 9 5G": (29, 31, 2020),
        "Redmi Note 9 Pro": (29, 31, 2020),
        "Redmi Note 9 Pro 5G": (29, 31, 2020),
        "Redmi Note 9 Pro Max": (29, 31, 2020),
        "Redmi Note 9S": (29, 31, 2020),
        "Redmi Note 9T 5G": (29, 31, 2021),
        "Redmi Note 10": (30, 33, 2021),  # Android 11, upgradable to 14
        "Redmi Note 10 5G": (30, 32, 2021),
        "Redmi Note 10 JE": (30, 31, 2021),
        "Redmi Note 10 Lite": (30, 31, 2021),
        "Redmi Note 10 Pro": (30, 33, 2021),
        "Redmi Note 10S": (30, 33, 2021),
        "Redmi Note 10T": (30, 32, 2021),
        "Redmi Note 10T 5G": (30, 32, 2021),
        "Redmi Note 10X": (29, 31, 2020),
        "Redmi Note 11 4G": (30, 33, 2022),
        "Redmi Note 11 5G": (30, 33, 2022),
        "Redmi Note 11 Pro": (30, 33, 2022),
        "Redmi Note 11 Pro 5G": (30, 33, 2022),
        "Redmi Note 11 Pro+": (30, 33, 2022),
        "Redmi Note 11 Pro+ 5G": (30, 33, 2022),
        "Redmi Note 11 SE": (30, 32, 2022),
        "Redmi Note 11E": (30, 32, 2022),
        "Redmi Note 11E Pro": (30, 32, 2022),
        "Redmi Note 11R 5G": (31, 33, 2022),
        "Redmi Note 11S": (30, 33, 2022),
        "Redmi Note 11S 5G": (30, 33, 2022),
        "Redmi Note 11T 5G": (30, 33, 2022),
        "Redmi Note 11T Pro": (31, 33, 2022),
        "Redmi Note 11T Pro+": (31, 33, 2022),
        "Redmi Note 12": (33, 34, 2023),  # Android 13
        "Redmi Note 12 Discovery": (33, 34, 2022),
        "Redmi Note 12 Pro": (33, 35, 2023),
        "Redmi Note 12 Pro DE": (33, 34, 2023),
        "Redmi Note 12 Pro Speed": (33, 34, 2023),
        "Redmi Note 12 Pro+": (33, 35, 2023),
        "Redmi Note 12 Pro+ 5G": (33, 35, 2023),
        "Redmi Note 12R": (33, 34, 2023),
        "Redmi Note 12R Pro": (33, 34, 2023),
        "Redmi Note 12S": (33, 34, 2023),
        "Redmi Note 12T": (33, 34, 2023),
        "Redmi Note 12T Pro": (33, 34, 2023),
        "Redmi Note 13": (33, 35, 2024),
        "Redmi Note 13 5G": (33, 35, 2024),
        "Redmi Note 13 Pro": (33, 35, 2024),
        "Redmi Note 13 Pro 5G": (33, 35, 2024),
        "Redmi Note 13 Pro+": (34, 35, 2024),
        "Redmi Note 13 Pro+ 5G": (34, 35, 2024),
        "Redmi Note 13R": (34, 35, 2024),
        "Redmi Note 13R Pro": (34, 35, 2024),
        "Redmi Note 14": (34, 35, 2024),
        "Redmi Note 14 5G": (34, 35, 2024),
        "Redmi Note 14 Pro": (34, 35, 2024),
        "Redmi Note 14 Pro 5G": (34, 35, 2024),
        "Redmi Note 14 Pro+": (34, 35, 2024),

        # === Redmi A series ===
        "Redmi A1": (31, 31, 2022),  # Android Go
        "Redmi A1+": (31, 31, 2022),
        "Redmi A2": (33, 33, 2023),  # Android Go
        "Redmi A2+": (33, 33, 2023),
        "Redmi A3": (34, 34, 2024),  # Android Go
        "Redmi A3x": (34, 34, 2024),

        # === Mi devices ===
        "Mi 4 LTE": (19, 23, 2014),
        "Mi 4i": (21, 23, 2015),
        "Mi 4W": (19, 23, 2014),
        "Mi 5X": (24, 27, 2017),
        "Mi 5s Plus": (23, 26, 2016),
        "Mi 8": (26, 29, 2018),
        "Mi 8 Explorer Edition": (26, 29, 2018),
        "Mi 8 Lite": (26, 29, 2018),
        "Mi 9": (28, 30, 2019),  # Android 9, upgradable to 11
        "Mi 9 Lite": (28, 30, 2019),
        "Mi 9 Pro 5G": (28, 30, 2019),
        "Mi 9 SE": (28, 30, 2019),
        "Mi 9 Transparent Edition": (28, 30, 2019),
        "Mi 9T Pro": (28, 30, 2019),
        "Mi 10": (29, 32, 2020),  # Android 10, upgradable to 13
        "Mi 10 Lite 5G": (29, 31, 2020),
        "Mi 10 Pro": (29, 32, 2020),
        "Mi 10 Ultra 5G": (29, 32, 2020),
        "Mi 10i": (30, 32, 2021),
        "Mi 10S": (30, 32, 2021),
        "Mi 10T 5G": (29, 32, 2020),
        "Mi 10T Lite 5G": (29, 31, 2020),
        "Mi 10T Pro 5G": (29, 32, 2020),
        "Mi 11": (30, 33, 2021),  # Android 11, upgradable to 14
        "Mi 11 Lite": (30, 33, 2021),
        "Mi 11 Lite 5G": (30, 33, 2021),
        "Mi 11 Lite 5G NE": (30, 33, 2021),
        "Mi 11 Pro": (30, 33, 2021),
        "Mi 11 Ultra": (30, 33, 2021),
        "Mi 11i": (30, 33, 2021),
        "Mi 11T": (30, 33, 2021),
        "Mi 11T Pro": (30, 33, 2021),
        "Mi 11X": (30, 33, 2021),
        "Mi 11X Pro": (30, 33, 2021),
        "Mi A2 Lite": (26, 29, 2018),
        "Mi A3": (28, 30, 2019),
        "Mi CC 9": (28, 29, 2019),
        "Mi CC 9 Pro": (28, 29, 2019),
        "Mi CC 9 Pro Premium Edition": (28, 29, 2019),
        "Mi CC 9e": (28, 29, 2019),
        "Mi Max": (23, 25, 2016),
        "Mi Max 3 Pro": (26, 28, 2018),
        "Mi Mix": (24, 26, 2016),
        "Mi Mix 2": (24, 28, 2017),
        "Mi Mix 2S": (26, 29, 2018),
        "Mi Mix 2S Art": (26, 29, 2018),
        "Mi Mix 3 5G": (28, 29, 2019),
        "Mi Mix 4": (30, 33, 2021),
        "Mi Mix Fold": (30, 33, 2021),
        "Mi Note 10": (28, 30, 2019),
        "Mi Note 10 Lite": (29, 30, 2020),
        "Mi Note 10 Pro": (28, 30, 2019),
        "Mi Note 3": (24, 27, 2017),
        "Mi Note Pro": (21, 23, 2015),
        "Mi One Plus": (16, 19, 2012),
        "Mi Play": (28, 29, 2019),

        # === Xiaomi numbered series (12, 13, 14, 15) ===
        "12": (31, 34, 2022),
        "12 Lite": (31, 33, 2022),
        "12 Pro": (31, 34, 2022),
        "12 Pro Dimensity": (31, 34, 2022),
        "12S": (31, 34, 2022),
        "12S Pro": (31, 34, 2022),
        "12S Ultra": (31, 34, 2022),
        "12T": (31, 34, 2022),
        "12T Pro": (31, 34, 2022),
        "12X": (31, 34, 2022),
        "13 Lite": (33, 35, 2023),
        "13 Pro": (33, 35, 2023),
        "13 Ultra": (33, 35, 2023),
        "13T": (33, 35, 2023),
        "13T Pro": (33, 35, 2023),
        "14": (34, 35, 2024),
        "14 Civi": (34, 35, 2024),
        "14 Pro": (34, 35, 2024),
        "14 Pro Ti": (34, 35, 2024),
        "14 Ultra": (34, 35, 2024),
        "14T Pro": (34, 35, 2024),
        "15": (35, 35, 2025),
        "15 Pro": (35, 35, 2025),

        # === Civi series ===
        "Civi": (30, 32, 2021),
        "Civi 1S": (31, 33, 2022),
        "Civi 2": (31, 33, 2022),
        "Civi 3": (33, 35, 2023),
        "Civi 4": (34, 35, 2024),
        "CC11": (30, 32, 2021),

        # === Mix Fold series ===
        "Mix Flip": (34, 35, 2024),
        "Mix Fold 2": (31, 34, 2022),
        "Mix Fold 3": (33, 35, 2023),
        "Mix Fold 4": (34, 35, 2024),

        # === Black Shark gaming phones ===
        "Black Shark": (26, 28, 2018),
        "Black Shark 2": (28, 30, 2019),
        "Black Shark 2 Pro": (28, 30, 2019),
        "Black Shark 3": (29, 31, 2020),
        "Black Shark 3 5G": (29, 31, 2020),
        "Black Shark 3 Pro": (29, 31, 2020),
        "Black Shark 3 Pro 5G": (29, 31, 2020),
        "Black Shark 4": (30, 32, 2021),
        "Black Shark 4 Pro": (30, 32, 2021),
        "Black Shark 5": (31, 33, 2022),
        "Black Shark 5 Pro": (31, 33, 2022),
        "Black Shark Helo": (26, 28, 2018),

        # === Pocophone/POCO ===
        "Pocophone F1": (26, 30, 2018),  # Android 8.1, upgradable to 11

        # === Qin feature phones ===
        "Qin 1s+": (28, 28, 2019),
        "Qin 2": (28, 28, 2019),
        "Qin 2 Pro": (28, 28, 2019),
        "Qin 3 Ultra": (30, 30, 2021),

        # === Pads ===
        "Mi Pad": (19, 21, 2014),
        "Mi Pad 2": (21, 23, 2015),
        "Mi Pad 3": (24, 26, 2017),
        "Mi Pad 4": (26, 28, 2018),
        "Mi Pad 4 Plus": (26, 28, 2018),
        "Mi Pad 4 WiFi": (26, 28, 2018),
        "Mi Pad 5": (30, 33, 2021),
        "Mi Pad 5 Pro": (30, 33, 2021),
        "Mi Pad 5 Pro 5G": (30, 33, 2021),
        "Note 12 Pro": (33, 34, 2022),
        "Pad 6 Max 14": (33, 35, 2023),
        "Pad 6 Pro": (33, 35, 2023),
        "Pad 6S Pro 12.4\"": (34, 35, 2024),
        "Redmi Pad": (31, 33, 2022),
        "Redmi Pad Pro": (34, 35, 2024),
        "Redmi Pad Pro 5G": (34, 35, 2024),
        "Redmi Pad SE": (33, 34, 2023),
        "Redmi Pad SE 8.7\"": (34, 35, 2024),

        # === Other ===
        "Redmi Turbo 3": (34, 35, 2024),
        "11i HyperCharge 5G": (30, 32, 2022),
    }

    # Xiaomi ecosystem
    xiaomi_devices = []
    for model in existing_models.get("xiaomi_ecosystem", []):
        # Check manual overrides first
        if model in xiaomi_manual_overrides:
            min_api, max_api, year = xiaomi_manual_overrides[model]
        # Determine device generation based on name patterns
        elif any(x in model for x in ["15", "14", "K80", "K70"]):
            min_api, max_api, year = (34, 35, 2024)
        elif any(x in model for x in ["13", "K60", "K50"]):
            min_api, max_api, year = (33, 35, 2023)
        elif any(x in model for x in ["12", "K40"]):
            min_api, max_api, year = (31, 34, 2022)
        elif any(x in model for x in [" 11", "11i", "K30", "K20"]):  # Note: space before 11 to avoid matching "11S"
            min_api, max_api, year = (29, 33, 2021)
        elif any(x in model for x in [" 10", "10T", "10S", "10i", "Mix 4", "Mix Fold"]):
            min_api, max_api, year = (28, 32, 2020)
        elif any(x in model for x in [" 9", "9T", "9 SE", "Mix 3", "Mix 2"]):
            min_api, max_api, year = (26, 30, 2019)
        elif any(x in model for x in [" 8", "Mi 8", "Mix"]):
            min_api, max_api, year = (24, 28, 2018)
        elif "Redmi" in model:
            # Redmi devices by number - more careful matching
            # Redmi Note series
            note_match = re.search(r'Redmi Note (\d+)', model)
            if note_match:
                num = int(note_match.group(1))
                if num >= 14:
                    min_api, max_api, year = (34, 35, 2024)
                elif num >= 13:
                    min_api, max_api, year = (33, 35, 2023)
                elif num >= 12:
                    min_api, max_api, year = (31, 34, 2022)
                elif num >= 11:
                    min_api, max_api, year = (30, 33, 2021)
                elif num >= 10:
                    min_api, max_api, year = (29, 32, 2020)
                elif num >= 9:
                    min_api, max_api, year = (28, 31, 2020)
                elif num >= 8:
                    min_api, max_api, year = (28, 30, 2019)
                else:
                    min_api, max_api, year = (23, 26, 2017)
            else:
                # Regular Redmi series
                num_match = re.search(r'Redmi (\d+)', model)
                if num_match:
                    num = int(num_match.group(1))
                    if num >= 14:
                        min_api, max_api, year = (34, 35, 2024)
                    elif num >= 13:
                        min_api, max_api, year = (33, 35, 2023)
                    elif num >= 12:
                        min_api, max_api, year = (31, 34, 2022)
                    elif num >= 11:
                        min_api, max_api, year = (30, 33, 2021)
                    elif num >= 10:
                        min_api, max_api, year = (29, 32, 2020)
                    elif num >= 9:
                        min_api, max_api, year = (28, 30, 2019)
                    elif num >= 7:
                        min_api, max_api, year = (26, 28, 2018)
                    elif num >= 5:
                        min_api, max_api, year = (23, 26, 2017)
                    elif num >= 4:
                        min_api, max_api, year = (21, 24, 2016)
                    else:
                        min_api, max_api, year = (19, 22, 2014)
                else:
                    # Redmi with letters (K series, A series, etc.)
                    if "K" in model:
                        k_match = re.search(r'K(\d+)', model)
                        if k_match:
                            k_num = int(k_match.group(1))
                            if k_num >= 70:
                                min_api, max_api, year = (34, 35, 2024)
                            elif k_num >= 60:
                                min_api, max_api, year = (33, 35, 2023)
                            elif k_num >= 50:
                                min_api, max_api, year = (31, 34, 2022)
                            elif k_num >= 40:
                                min_api, max_api, year = (30, 33, 2021)
                            elif k_num >= 30:
                                min_api, max_api, year = (29, 32, 2020)
                            else:
                                min_api, max_api, year = (28, 30, 2019)
                        else:
                            min_api, max_api, year = (30, 34, 2021)
                    elif "A" in model:
                        # Redmi A series (budget)
                        min_api, max_api, year = (31, 33, 2023)
                    elif "Pad" in model:
                        min_api, max_api, year = (31, 34, 2023)
                    elif "Turbo" in model:
                        min_api, max_api, year = (34, 35, 2024)
                    else:
                        min_api, max_api, year = (30, 34, 2021)
        else:
            min_api, max_api, year = (30, 34, 2021)  # Default

        # Newer flagships are more popular
        popularity = 0.15 if year >= 2024 else (0.1 if year >= 2022 else 0.05)

        xiaomi_devices.append({
            "model_code": model,
            "brand": "xiaomi",
            "name": model,
            "min_android_api": min_api,
            "max_android_api": max_api,
            "popularity": popularity,
            "year": year
        })

    result["xiaomi_ecosystem"] = xiaomi_devices

    return result


def normalize_popularity(devices: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """
    Normalize popularity scores within each brand category.

    Makes sure weights sum to 1.0 within each category.
    """
    for brand, device_list in devices.items():
        total = sum(d['popularity'] for d in device_list)
        if total > 0:
            for d in device_list:
                d['popularity'] = d['popularity'] / total

    return devices


def main():
    """Main script execution."""
    print("=" * 60)
    print("Android Device Specifications Generator")
    print("=" * 60)

    # Generate estimated specs from existing device models
    print("\nGenerating estimated Android version specs from existing devices...")
    devices = generate_estimated_specs()

    # Normalize popularity scores
    devices = normalize_popularity(devices)

    # Calculate statistics
    total_devices = sum(len(v) for v in devices.values())
    print(f"\nProcessed {total_devices} devices across {len(devices)} brands:")

    for brand, device_list in devices.items():
        api_range = (
            min(d['min_android_api'] for d in device_list),
            max(d['max_android_api'] for d in device_list)
        )
        print(f"  {brand}: {len(device_list)} devices, API range {api_range[0]}-{api_range[1]}")

    # Build final output structure
    output = {
        "meta": {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_devices": total_devices,
            "source": "estimated from device model patterns"
        },
        "api_to_version": API_TO_ANDROID_VERSION,
        "devices": devices
    }

    # Save to data directory
    output_path = Path(__file__).parent.parent / "uaforge" / "data" / "android_device_specs.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved device specifications to {output_path}")

    # Also output a simplified version for quick validation
    sample_output = {}
    for brand, devices_list in devices.items():
        sample_output[brand] = devices_list[:3]  # First 3 of each

    print("\nSample output:")
    print(json.dumps(sample_output, indent=2))


if __name__ == "__main__":
    main()

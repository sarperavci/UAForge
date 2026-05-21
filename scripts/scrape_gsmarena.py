#!/usr/bin/env python3
"""
GSMArena Async Scraper - Fast concurrent scraping of device specifications.

Features:
- Async/concurrent scraping with aiohttp
- Realistic Windows Chrome headers
- Extracts: model codes, Android versions, RAM, CPU, chipset
- Rate limiting with semaphore
- Progress tracking
"""

import asyncio
import aiohttp
import json
import re
import time
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from bs4 import BeautifulSoup
import ssl

# Android version to API level mapping
ANDROID_VERSION_TO_API = {
    "1.0": 1, "1.1": 2, "1.5": 3, "1.6": 4, "2.0": 5, "2.0.1": 6, "2.1": 7,
    "2.2": 8, "2.3": 9, "2.3.3": 10, "3.0": 11, "3.1": 12, "3.2": 13,
    "4.0": 14, "4.0.3": 15, "4.1": 16, "4.2": 17, "4.3": 18, "4.4": 19,
    "5.0": 21, "5.1": 22, "6.0": 23, "7.0": 24, "7.1": 25, "8.0": 26,
    "8.1": 27, "9": 28, "9.0": 28, "10": 29, "11": 30, "12": 31, "12L": 32,
    "13": 33, "14": 34, "15": 35, "16": 36
}

API_TO_ANDROID_VERSION = {v: k for k, v in ANDROID_VERSION_TO_API.items()}

# Realistic Windows Chrome headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# Concurrency settings - be gentle to avoid rate limiting
MAX_CONCURRENT_REQUESTS = 3
REQUEST_DELAY = 2.0  # seconds between requests


@dataclass
class DeviceInfo:
    model_code: str
    brand: str
    name: str
    min_android_api: int
    max_android_api: int
    popularity: float
    year: int
    ram_gb: List[int] = field(default_factory=list)
    cpu_cores: int = 0
    chipset: str = ""
    storage_gb: List[int] = field(default_factory=list)


def parse_android_version(os_string: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse Android version string to extract min and max API levels.

    Examples:
        "Android 9.0 (Pie), upgradable to Android 11" -> (28, 30)
        "Android 9.0, up to Android 10, MIUI 12" -> (28, 29)
        "Android 14, One UI 6" -> (34, 34)
    """
    if not os_string or "Android" not in os_string:
        return None, None

    os_string = os_string.replace('\n', ' ').replace('\r', ' ')

    # Find all Android version patterns
    versions = re.findall(r'Android (\d+(?:\.\d+)?)', os_string)

    if not versions:
        return None, None

    api_levels = []
    for v in versions:
        parts = v.split('.')
        # For old versions like 4.4, 5.1
        if len(parts) >= 2 and int(parts[0]) < 10:
            normalized = f"{parts[0]}.{parts[1]}"
        else:
            normalized = parts[0]

        api = ANDROID_VERSION_TO_API.get(normalized)
        if not api:
            api = ANDROID_VERSION_TO_API.get(parts[0])
        if api:
            api_levels.append(api)

    if not api_levels:
        return None, None

    return min(api_levels), max(api_levels)


def parse_ram(ram_string: str) -> List[int]:
    """Extract RAM sizes in GB from string like '6/8' or '6GB RAM'."""
    if not ram_string:
        return []

    # Match patterns like "6/8", "6GB", "6 GB"
    matches = re.findall(r'(\d+)\s*(?:GB)?', ram_string)
    return [int(m) for m in matches if 1 <= int(m) <= 24]


def parse_storage(storage_string: str) -> List[int]:
    """Extract storage sizes in GB from string."""
    if not storage_string:
        return []

    # Match patterns like "64GB", "128GB", "256GB"
    matches = re.findall(r'(\d+)\s*GB', storage_string, re.IGNORECASE)
    return [int(m) for m in matches if 16 <= int(m) <= 2048]


def parse_cpu_cores(cpu_string: str) -> int:
    """Extract CPU core count from string like 'Octa-core' or 'Quad-core'."""
    if not cpu_string:
        return 0

    cpu_lower = cpu_string.lower()
    if 'octa' in cpu_lower:
        return 8
    elif 'hexa' in cpu_lower:
        return 6
    elif 'quad' in cpu_lower:
        return 4
    elif 'dual' in cpu_lower:
        return 2
    elif 'single' in cpu_lower:
        return 1

    # Try to find pattern like "8x" or "4x"
    match = re.search(r'(\d+)x', cpu_string, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return 0


def parse_year(date_string: str) -> Optional[int]:
    """Extract year from date string."""
    if not date_string:
        return None

    match = re.search(r'20\d{2}', date_string)
    return int(match.group()) if match else None


def parse_hits(hits_string: str) -> int:
    """Parse hits count from string like '2,960,930 hits'."""
    if not hits_string:
        return 0

    match = re.search(r'([\d,]+)\s*hits', hits_string, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(',', ''))
    return 0


def parse_device_page(html: str, brand: str) -> Optional[DeviceInfo]:
    """Parse a device page using BeautifulSoup."""
    soup = BeautifulSoup(html, 'html.parser')

    # Get device name
    name_elem = soup.find('h1', {'data-spec': 'modelname'})
    if not name_elem:
        return None
    name = name_elem.get_text(strip=True)

    # Get OS info
    os_elem = soup.find('td', {'data-spec': 'os'})
    os_string = os_elem.get_text(strip=True) if os_elem else ""

    min_api, max_api = parse_android_version(os_string)
    if min_api is None:
        return None  # Not an Android device

    # Get model codes
    models_elem = soup.find('td', {'data-spec': 'models'})
    models_string = models_elem.get_text(strip=True) if models_elem else ""

    # Extract model codes based on brand patterns
    model_codes = []
    if brand == "samsung":
        model_codes = re.findall(r'SM-[A-Z]\d{3,4}[A-Z0-9]*', models_string)
    elif brand == "xiaomi_ecosystem":
        # Xiaomi uses various patterns
        model_codes = re.findall(r'[A-Z0-9]{6,12}(?:[A-Z]{2})?', models_string)
        if not model_codes:
            model_codes = re.findall(r'M\d{4}[A-Z0-9]+', models_string)
    elif brand == "google_pixel":
        model_codes = re.findall(r'G[A-Z0-9]{3,6}', models_string)
    elif brand == "oppo_realme_generic":
        model_codes = re.findall(r'CPH\d{4}|RMX\d{4}|PEEM\d{2}|PEGM\d{2}', models_string)

    # Use device name as fallback model code
    model_code = model_codes[0] if model_codes else name

    # Get release year
    year_elem = soup.find('td', {'data-spec': 'year'})
    year_string = year_elem.get_text(strip=True) if year_elem else ""
    year = parse_year(year_string) or 2020

    # Get RAM
    ram_elem = soup.find('span', {'data-spec': 'ramsize-hl'})
    ram_string = ram_elem.get_text(strip=True) if ram_elem else ""
    ram_sizes = parse_ram(ram_string)

    # Also check internal memory for RAM info
    internal_elem = soup.find('td', {'data-spec': 'internalmemory'})
    internal_string = internal_elem.get_text(strip=True) if internal_elem else ""
    if not ram_sizes:
        # Parse from internal memory like "64GB 6GB RAM"
        ram_matches = re.findall(r'(\d+)\s*GB\s*RAM', internal_string, re.IGNORECASE)
        ram_sizes = list(set([int(m) for m in ram_matches]))

    # Get storage
    storage_sizes = parse_storage(internal_string)

    # Get CPU
    cpu_elem = soup.find('td', {'data-spec': 'cpu'})
    cpu_string = cpu_elem.get_text(strip=True) if cpu_elem else ""
    cpu_cores = parse_cpu_cores(cpu_string)

    # Get chipset
    chipset_elem = soup.find('td', {'data-spec': 'chipset'})
    chipset = chipset_elem.get_text(strip=True) if chipset_elem else ""

    # Get popularity (hits)
    hits_elem = soup.find('li', class_='help-popularity')
    hits_string = hits_elem.get_text(strip=True) if hits_elem else ""
    hits = parse_hits(hits_string)

    popularity = hits / 10_000_000 if hits else 0.01

    return DeviceInfo(
        model_code=model_code,
        brand=brand,
        name=name,
        min_android_api=min_api,
        max_android_api=max_api,
        popularity=popularity,
        year=year,
        ram_gb=ram_sizes,
        cpu_cores=cpu_cores,
        chipset=chipset,
        storage_gb=storage_sizes
    )


def parse_device_list(html: str) -> List[Tuple[str, str]]:
    """Parse brand device list page to get device URLs and names."""
    soup = BeautifulSoup(html, 'html.parser')
    devices = []

    # Find all device links in the makers container
    makers_div = soup.find('div', class_='makers')
    if not makers_div:
        return devices

    for link in makers_div.find_all('a'):
        href = link.get('href', '')
        if href and href.endswith('.php') and 'compare' not in href:
            name_span = link.find('span')
            name = name_span.get_text(strip=True) if name_span else ""
            if name:
                devices.append((href, name))

    return devices


async def fetch_page(session: aiohttp.ClientSession, url: str, semaphore: asyncio.Semaphore, retries: int = 3) -> Optional[str]:
    """Fetch a page with rate limiting and retries."""
    for attempt in range(retries):
        async with semaphore:
            await asyncio.sleep(REQUEST_DELAY + random.uniform(0.5, 1.5))

            try:
                async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:
                        wait_time = 30 * (attempt + 1)
                        print(f"  Rate limited (attempt {attempt+1}), waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"  HTTP {response.status} for {url}")
                        return None
            except asyncio.TimeoutError:
                print(f"  Timeout on {url} (attempt {attempt+1})")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"  Error fetching {url}: {e}")
                await asyncio.sleep(5)

    return None


async def scrape_device(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore,
                        url: str, brand: str) -> Optional[DeviceInfo]:
    """Scrape a single device page."""
    full_url = f"https://www.gsmarena.com/{url}"
    html = await fetch_page(session, full_url, semaphore)

    if not html:
        return None

    return parse_device_page(html, brand)


async def get_all_device_urls(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore,
                               brand: str, base_url: str, max_pages: int = 10) -> List[Tuple[str, str]]:
    """Get all device URLs from paginated brand listings."""
    all_devices = []

    # Parse brand ID from URL (e.g., "samsung-phones-9.php" -> "9")
    brand_match = re.search(r'-(\d+)\.php', base_url)
    brand_id = brand_match.group(1) if brand_match else ""

    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"https://www.gsmarena.com/{base_url}"
        else:
            # Pattern: samsung-phones-f-9-0-p2.php
            base_name = base_url.replace('.php', '').replace(f'-{brand_id}', '')
            url = f"https://www.gsmarena.com/{base_name}-f-{brand_id}-0-p{page}.php"

        print(f"  Fetching page {page}...", end=" ", flush=True)
        html = await fetch_page(session, url, semaphore)

        if not html:
            print("failed")
            break

        devices = parse_device_list(html)
        print(f"found {len(devices)} devices")

        if not devices:
            break

        all_devices.extend(devices)

        # Check if there's a next page
        if 'class="pages-next"' not in html and f'p{page + 1}' not in html:
            break

    return all_devices


async def scrape_brand(brand: str, base_url: str, max_devices: int = 200, max_pages: int = 15) -> List[DeviceInfo]:
    """Scrape all devices for a brand."""
    print(f"\n{'='*60}")
    print(f"Scraping {brand}")
    print(f"{'='*60}")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    connector = aiohttp.TCPConnector(ssl=ssl_context, limit=MAX_CONCURRENT_REQUESTS)

    async with aiohttp.ClientSession(connector=connector) as session:
        # Get all device URLs
        device_urls = await get_all_device_urls(session, semaphore, brand, base_url, max_pages)
        print(f"Total devices found: {len(device_urls)}")

        if not device_urls:
            return []

        # Limit devices
        device_urls = device_urls[:max_devices]

        # Scrape devices concurrently
        print(f"Scraping {len(device_urls)} devices concurrently...")

        tasks = [
            scrape_device(session, semaphore, url, brand)
            for url, name in device_urls
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        devices = []
        for i, result in enumerate(results):
            if isinstance(result, DeviceInfo):
                devices.append(result)
            elif isinstance(result, Exception):
                print(f"  Error: {result}")

        print(f"Successfully scraped: {len(devices)} devices")
        return devices


async def main():
    print("=" * 70)
    print("GSMArena Async Device Scraper")
    print("=" * 70)

    start_time = time.time()
    all_devices = {}

    # Brand configurations (reduced for faster scraping)
    brands = [
        ("samsung", "samsung-phones-9.php", 100, 8),
        ("google_pixel", "google-phones-107.php", 30, 3),
        ("xiaomi_ecosystem", "xiaomi-phones-80.php", 100, 8),
        ("oppo_realme_generic", "oppo-phones-82.php", 50, 5),
    ]

    for brand_key, base_url, max_devices, max_pages in brands:
        try:
            devices = await scrape_brand(brand_key, base_url, max_devices, max_pages)
            if devices:
                all_devices[brand_key] = [asdict(d) for d in devices]
        except Exception as e:
            print(f"Error scraping {brand_key}: {e}")

    # Also scrape Realme
    try:
        realme_devices = await scrape_brand("realme", "realme-phones-118.php", 50, 5)
        if realme_devices:
            existing = all_devices.get("oppo_realme_generic", [])
            # Change brand to oppo for consistency
            for d in realme_devices:
                d.brand = "oppo"
            existing.extend([asdict(d) for d in realme_devices])
            all_devices["oppo_realme_generic"] = existing
    except Exception as e:
        print(f"Error scraping Realme: {e}")

    # Normalize popularity within each brand
    for brand, device_list in all_devices.items():
        total = sum(d['popularity'] for d in device_list)
        if total > 0:
            for d in device_list:
                d['popularity'] = d['popularity'] / total

    # Build output
    output = {
        "meta": {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "GSMArena async scrape",
            "total_devices": sum(len(v) for v in all_devices.values()),
            "scrape_time_seconds": round(time.time() - start_time, 1)
        },
        "api_to_version": API_TO_ANDROID_VERSION,
        "devices": all_devices
    }

    # Save
    output_path = Path(__file__).parent.parent / "uaforge" / "data" / "android_device_specs.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"Completed in {elapsed:.1f} seconds")
    print(f"Saved {output['meta']['total_devices']} devices to {output_path}")
    print(f"{'='*70}")

    # Print summary
    for brand, devices in all_devices.items():
        if devices:
            min_api = min(d['min_android_api'] for d in devices)
            max_api = max(d['max_android_api'] for d in devices)
            print(f"  {brand}: {len(devices)} devices, API {min_api}-{max_api}")

    # Show some sample devices
    print(f"\nSample devices:")
    for brand in ["xiaomi_ecosystem", "samsung"]:
        devices = all_devices.get(brand, [])
        for d in devices[:2]:
            print(f"  {d['name']}: API {d['min_android_api']}-{d['max_android_api']}, "
                  f"RAM: {d.get('ram_gb', [])}, CPU: {d.get('cpu_cores', 0)} cores")


if __name__ == "__main__":
    asyncio.run(main())

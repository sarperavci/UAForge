#!/usr/bin/env python3

import re
import json
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple

def parse_caniuse_html(html_content: str) -> Dict[str, List[Dict[str, float]]]:
    """
    Parse the caniuse HTML content and extract browser market share data.

    Args:
        html_content: The HTML content from caniuse.com usage table

    Returns:
        Dictionary mapping browser keys to list of version/share dictionaries
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Mapping from caniuse browser classes to our format
    browser_mapping = {
        'chrome': 'chrome',
        'edge': 'edge',
        'safari': 'safari',
        'firefox': 'firefox',
        'opera': 'opera',
        'ie': 'ie',
        'and_chr': 'and_chr',  # Chrome for Android
        'ios_saf': 'ios_saf',  # Safari on iOS
        'samsung': 'samsung',
        'op_mob': 'op_mob',    # Opera Mobile
        'and_uc': 'and_uc',    # UC Browser for Android
        'android': 'android',  # Android Browser
        'and_ff': 'and_ff',    # Firefox for Android
    }

    results = {}

    # Find all browser sections
    browser_sections = soup.find_all('div', class_='support-list')

    for section in browser_sections:
        heading = section.find('h4', class_=re.compile(r'browser-heading'))
        if not heading:
            continue

        # Extract browser class name
        browser_classes = [cls for cls in heading.get('class', []) if cls.startswith('browser--')]
        if not browser_classes:
            continue

        browser_class = browser_classes[0].replace('browser--', '')

        # Map to our format or skip if not recognized
        if browser_class not in browser_mapping:
            print(f"Skipping unrecognized browser: {browser_class}")
            continue

        mapped_browser = browser_mapping[browser_class]

        # Find all version entries in this section
        version_entries = section.find_all('li', class_='stat-cell')

        browser_versions = []
        for entry in version_entries:
            # Extract version number from the label
            label_elem = entry.find('b', class_='stat-cell__label')
            percentage_elem = entry.find('span', class_='stat-cell__percentage')

            if label_elem and percentage_elem:
                version_str = label_elem.get_text(strip=True).rstrip(':')

                # Extract percentage and convert to float
                percentage_text = percentage_elem.get_text(strip=True)
                # Remove % sign and convert to float
                percentage_match = re.search(r'([\d.]+)', percentage_text)
                if percentage_match:
                    percentage = float(percentage_match.group(1))

                    # Only add if percentage is greater than 0
                    if percentage > 0:
                        browser_versions.append({
                            "version": version_str,
                            "global_share": percentage
                        })

        if browser_versions:
            results[mapped_browser] = browser_versions

    return results


def filter_low_shares(data: Dict[str, List[Dict[str, float]]], min_share: float = 0.1) -> Dict[str, List[Dict[str, float]]]:
    """
    Filter out entries with share less than min_share percent.

    Args:
        data: Browser share data dictionary
        min_share: Minimum share percentage (default 0.1%)

    Returns:
        Filtered data dictionary
    """
    filtered_data = {}

    for browser, versions in data.items():
        filtered_versions = [v for v in versions if v["global_share"] >= min_share]
        if filtered_versions:
            filtered_data[browser] = filtered_versions

    return filtered_data


def normalize_shares(data: Dict[str, List[Dict[str, float]]]) -> Dict[str, List[Dict[str, float]]]:
    """
    Normalize shares so they sum to 100% across all browsers.

    Args:
        data: Browser share data dictionary

    Returns:
        Normalized data dictionary
    """
    # Calculate total of all shares
    total_share = 0.0
    for browser, versions in data.items():
        for version in versions:
            total_share += version["global_share"]

    if total_share == 0:
        return data

    # Normalize each share
    normalized_data = {}
    for browser, versions in data.items():
        normalized_versions = []
        for version in versions:
            normalized_version = {
                "version": version["version"],
                "global_share": (version["global_share"] / total_share) * 100.0
            }
            normalized_versions.append(normalized_version)
        normalized_data[browser] = normalized_versions

    return normalized_data


def generate_mobile_chrome_from_desktop(desktop_data: List[Dict[str, float]],
                                       existing_mobile: List[Dict[str, float]]) -> List[Dict[str, float]]:
    """
    Generate more mobile Chrome versions based on desktop versions.
    This creates additional mobile versions that mirror popular desktop versions.

    Args:
        desktop_data: List of desktop Chrome versions with shares
        existing_mobile: Existing mobile Chrome versions

    Returns:
        Combined list of mobile Chrome versions
    """
    # Create a set of existing mobile versions to avoid duplicates
    existing_mobile_versions = {item["version"] for item in existing_mobile}

    # Add mobile versions based on desktop versions
    new_mobile_versions = existing_mobile.copy()

    for desktop_version in desktop_data:
        version = desktop_version["version"]
        share = desktop_version["global_share"]

        # Only add if not already exists and is a recent version
        if version not in existing_mobile_versions:
            # Adjust share for mobile (typically mobile has similar but slightly different distribution)
            # For now, we'll use the same share, but in practice you might want to adjust this
            new_mobile_versions.append({
                "version": version,
                "global_share": share
            })

    return new_mobile_versions


async def fetch_caniuse_data():
    """
    Fetch the caniuse.com usage table data asynchronously.
    """
    import aiohttp

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Brave";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'sec-gpc': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    }

    async with aiohttp.ClientSession() as session:
        async with session.get('https://caniuse.com/usage-table', headers=headers) as response:
            if response.status == 200:
                html_content = await response.text()
                return html_content
            else:
                raise Exception(f"Failed to fetch data: HTTP {response.status}")


async def main():
    # Fetch the HTML content from caniuse.com
    print("Fetching data from caniuse.com...")
    try:
        html_content = await fetch_caniuse_data()
        print("Data fetched successfully!")
    except Exception as e:
        print(f"Error fetching data: {e}")
        raise RuntimeError(f"Could not fetch data from caniuse.com: {e}")

    # Parse the HTML
    parsed_data = parse_caniuse_html(html_content)

    print("Parsed browser data:")
    for browser, versions in parsed_data.items():
        print(f"{browser}: {len(versions)} versions")
        for version in versions[:3]:  # Show first 3 versions as sample
            print(f"  {version['version']}: {version['global_share']}%")
        if len(versions) > 3:
            print(f"  ... and {len(versions) - 3} more")

    # Generate more mobile Chrome versions based on desktop versions
    if 'chrome' in parsed_data and 'and_chr' in parsed_data:
        parsed_data['and_chr'] = generate_mobile_chrome_from_desktop(
            parsed_data['chrome'],
            parsed_data['and_chr']
        )
        print(f"\nAfter generating mobile Chrome versions: {len(parsed_data['and_chr'])} versions")

    # Filter out entries with share less than 0.1%
    filtered_data = filter_low_shares(parsed_data, min_share=0.1)

    print(f"\nAfter filtering low shares (< 0.1%):")
    for browser, versions in filtered_data.items():
        print(f"{browser}: {len(versions)} versions")

    # Normalize the shares
    normalized_data = normalize_shares(filtered_data)

    # Calculate total to verify normalization
    total_after_normalization = 0.0
    for browser, versions in normalized_data.items():
        for version in versions:
            total_after_normalization += version["global_share"]

    print(f"\nTotal share after normalization: {total_after_normalization:.2f}%")

    # Write to market_share.json with minified JSON
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Move up one level from scripts/ to repo root
    repo_root = os.path.dirname(current_dir)
    output_file = os.path.join(repo_root, 'uaforge', 'data', 'market_share.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(normalized_data, f, separators=(',', ':'))  # Minified JSON

    print(f"\nMinified data written to {output_file}")

    # Also print a summary
    print("\nSummary of top browser versions:")
    for browser, versions in normalized_data.items():
        sorted_versions = sorted(versions, key=lambda x: x['global_share'], reverse=True)
        print(f"\n{browser.upper()}:")
        for version in sorted_versions[:5]:  # Top 5 versions
            print(f"  {version['version']}: {version['global_share']:.3f}%")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
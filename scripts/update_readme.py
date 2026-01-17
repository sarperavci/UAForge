#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime

# Browser display names mapping
BROWSER_NAMES = {
    "chrome": "Chrome (Desktop)",
    "edge": "Edge",
    "safari": "Safari (Desktop)",
    "firefox": "Firefox",
    "opera": "Opera",
    "ie": "IE",
    "and_chr": "Chrome for Android",
    "ios_saf": "iOS Safari",
    "samsung": "Samsung Internet",
    "op_mob": "Opera Mobile",
    "and_uc": "UC Browser",
    "android": "Android Browser",
    "and_ff": "Firefox for Android",
}


def load_market_share(json_path: str) -> dict:
    """Load market share data from JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_browser_totals(data: dict) -> list[tuple[str, float]]:
    """Calculate total market share for each browser."""
    totals = {}
    for browser_key, versions in data.items():
        total = sum(v["global_share"] for v in versions)
        display_name = BROWSER_NAMES.get(browser_key, browser_key)
        totals[display_name] = total

    # Sort by market share descending
    sorted_totals = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    return sorted_totals


def generate_table(browser_totals: list[tuple[str, float]]) -> str:
    """Generate markdown table from browser totals."""
    lines = [
        "## Current Market Share Distribution",
        "",
        "The table below shows the aggregated browser market share from the current dataset. Data is sourced from caniuse.com and updated automatically.",
        "",
        "| Browser | Market Share |",
        "|---------|-------------|",
    ]

    for browser, share in browser_totals:
        lines.append(f"| {browser} | {share:.2f}% |")

    # Add last updated date
    today = datetime.now().strftime("%d-%m-%Y")
    lines.append("")
    lines.append(f"*Last updated: {today}*")

    return "\n".join(lines)


def update_readme(readme_path: str, new_section: str) -> bool:
    """
    Update the README with the new market share section.
    Returns True if changes were made, False otherwise.
    """
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern to match the entire market share section
    pattern = r"## Current Market Share Distribution.*?\*Last updated: \d{2}-\d{2}-\d{4}\*"

    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, new_section, content, flags=re.DOTALL)
    else:
        # Section doesn't exist, append before License section
        license_pattern = r"(## License)"
        if re.search(license_pattern, content):
            new_content = re.sub(
                license_pattern, f"{new_section}\n\n\\1", content
            )
        else:
            # Just append at the end
            new_content = content + "\n\n" + new_section

    if new_content != content:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True

    return False


def main():
    # Get paths relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)

    market_share_path = os.path.join(
        repo_root, "uaforge", "data", "market_share.json"
    )
    readme_path = os.path.join(repo_root, "README.md")

    print(f"Loading market share data from {market_share_path}")
    data = load_market_share(market_share_path)

    print("Calculating browser totals...")
    totals = calculate_browser_totals(data)

    print("\nBrowser Market Share:")
    for browser, share in totals:
        print(f"  {browser}: {share:.2f}%")

    print(f"\nUpdating README at {readme_path}")
    new_section = generate_table(totals)

    if update_readme(readme_path, new_section):
        print("README updated successfully!")
    else:
        print("No changes needed in README.")


if __name__ == "__main__":
    main()

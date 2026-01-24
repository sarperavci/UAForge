# UAForge

**Enterprise-grade, deterministic User Agent & Client Hint generator based on real-world browser statistics**

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Auto-Updated](https://img.shields.io/badge/data-auto--updated%20weekly-orange)](https://caniuse.com/usage-table)

---

Most "random user-agent" libraries are broken. They generate outdated browser strings, mix incompatible OS combinations, or lack the modern headers that fingerprinting systems now check.

**UAForge takes a different approach.** Instead of picking random strings, it simulates real users based on **statistical probability**. If Chrome 143 on Android holds 40% global market share, UAForge generates that identity 40% of the time.

It also generates matching **Client Hints (`Sec-CH-UA`)** headers automatically—allowing your automation to pass modern fingerprinting checks that go beyond the legacy User-Agent string.

### Key Features

*   **Statistically Accurate** — Weighted by real-world global usage data, updated weekly from caniuse.com
*   **Smart Correlations** — Enforces valid browser↔OS mappings (no Safari on Windows)
*    **Real Hardware** — Injects actual device models (Pixel 9, Galaxy S24, etc.) for mobile agents
*   **Client Hints** — Generates Sec-CH-UA, Sec-CH-UA-Mobile, Sec-CH-UA-Platform, and GREASE tokens
*    **Deterministic** — Seed support for consistent, reproducible identities across sessions


## Installation

```bash
pip install git+https://github.com/sarperavci/uaforge.git
```

*Note:* The repo does not contain the market-share data files due to size constraints. They are automatically downloaded from the release assets while installing.


## Quick Start

The API is designed to be simple. You generate an "Identity" object, which contains everything you need for your requests.

```python
from uaforge.core.generator import UserAgentGenerator

# 1. Initialize the generator
agent = UserAgentGenerator()

# 2. Generate an identity
identity = agent.generate()

# 3. Get the headers (includes User-Agent AND Client Hints)
headers = identity.get_headers()
full_client_hints = identity.get_all_client_hints()

# Use with requests/httpx
# response = requests.get("https://httpbin.org/headers", headers=headers)

print(f"Browser: {identity.meta_browser.value}")
print(f"OS:      {identity.meta_os.value}")
print(headers)
print(full_client_hints)
```

### Sample Output

Default Headers:

```json
{
"User-Agent": "Mozilla/5.0 (Linux; Android 13; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
"Sec-CH-UA": "\"Not A Brand\";v=\"99\", \"Chromium\";v=\"144\", \"Google Chrome\";v=\"144\"",
"Sec-CH-UA-Mobile": "?1",
"Sec-CH-UA-Platform": "\"Android\""
}
```

Full Client Hints:

```json
{
"Sec-CH-UA": "\"Not A Brand\";v=\"99\", \"Chromium\";v=\"144\", \"Google Chrome\";v=\"144\"",
"Sec-CH-UA-Mobile": "?1",
"Sec-CH-UA-Platform": "\"Android\"",
"Sec-CH-UA-Full-Version-List": "\"Not A Brand\";v=\"99.0.0.0\", \"Chromium\";v=\"144.0.7559.59\", \"Google Chrome\";v=\"144.0.7559.59\"",
"Sec-CH-UA-Platform-Version": "13.0.0",
"Sec-CH-UA-Model": "\"Pixel 9\"",
"Sec-CH-UA-Arch": "\"arm\"",
"Sec-CH-UA-Bitness": "\"64\"",
"Sec-CH-UA-Full-Version": "\"144.0.7559.59\"",
"Sec-CH-UA-Form-Factors": "\"Mobile\"",
"Sec-CH-UA-WoW64": "?0",
"Sec-CH-Prefers-Color-Scheme": "dark"
}
```

## Advanced Usage

### Deterministic Generation (Sessions)
If you are managing long-running sessions, you need the User Agent to stay consistent across restarts. Use a seed.

```python
# The identity generated here will ALWAYS be the same for seed 42
user = UserAgentGenerator(seed=42).generate()

print(user.user_agent) 
# Useful for associating a UA with a specific database UserID
```

### Accessing Granular Data
Sometimes you need just the OS version or just the device model for analytics.

```python
identity = agent.generate()

if identity.meta_device == "mobile":
    print(f"Device Model: {identity.ch_model}")  # e.g. "Pixel 8 Pro"
    print(f"Architecture: {identity.ch_arch}")   # e.g. "arm"
```

## How it works

### The Data Sources

We don't guess. We utilize three distinct data layers:

1.  **`market_share.json`**: Global browser usage stats (Chrome, Safari, Edge, Firefox).
2.  **`os_distribution.json`**: The probability of an OS given a specific browser (e.g., Safari is 100% macOS/iOS, but Chrome is split between Windows, Mac, Linux, and Android).
3.  **`device_models.json`**: A curated list of ~500 real-world mobile device fingerprints.

## Maintenance & Updates

The browser ecosystem moves fast. Market share data is **automatically updated weekly** via GitHub Actions by parsing the latest data from [caniuse.com](https://caniuse.com/usage-table).

You can also trigger a manual update by running:
```bash
python scripts/parse_caniuse.py
```

## Current Market Share Distribution

The table below shows the aggregated browser market share from the current dataset. Data is sourced from caniuse.com and updated automatically.

| Browser | Market Share |
|---------|-------------|
| Chrome for Android | 58.89% |
| Chrome (Desktop) | 21.89% |
| iOS Safari | 9.62% |
| Edge | 3.30% |
| Samsung Internet | 1.48% |
| Firefox | 1.39% |
| Opera Mobile | 0.70% |
| Opera | 0.65% |
| Safari (Desktop) | 0.63% |
| Android Browser | 0.46% |
| UC Browser | 0.42% |
| IE | 0.30% |
| Firefox for Android | 0.26% |

*Last updated: 23-01-2026*

## License

MIT License. Feel free to use this in your commercial scrapers, bots or testing suites.
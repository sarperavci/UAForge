# UAForge

**Enterprise-grade, deterministic User Agent & Client Hint generator based on real-world census data as of December 2025**

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green)
![Data Updated](https://img.shields.io/badge/market%20share-Dec%202025-orange)

Let's be honest: most "random user-agent" libraries are bad. They pick 10-year-old browser strings, mix incompatible operating systems or fail to provide the modern headers that security systems actually check.

**UAForge** is different. It doesn't just pick a random string. it simulates a user based on **statistical probability**. If Chrome 142 on Windows 10 has a 13% global market share, UAForge will generate that identity exactly 13% of the time.

More importantly, it generates the **Client Hints (`Sec-CH-UA`)** that match the legacy User-Agent string perfectly, allowing your scrapers or automation to pass deep fingerprinting checks.

### Why use this?

*   **Statistically Accurate:** Candidates are weighted by real-world global usage data (Snapshot: Dec 12, 2025).
*   **Smart Correlations:** Enforces valid Browser-to-OS mappings to prevent unrealistic combinations.
*   **Real Hardware:** Injects actual device models (e.g., Pixel 9, Samsung S29) for mobile agents.
*   **Client Hints:** Automatically generates modern headers (Sec-CH-UA, Mobile, Platform) and GREASE tokens.
*   **Deterministic:** Supports seeding to generate consistent, persistent identities for long-running sessions.

---

## Installation

```bash
pip install git+https://github.com/sarperavci/uaforge.git
```

---

## Quick Start

The API is designed to be simple. You generate an "Identity" object, which contains everything you need for your requests.

```python
from market_agent.core.generator import UserAgentGenerator

# 1. Initialize the generator
agent = UserAgentGenerator()

# 2. Generate an identity
identity = agent.generate()

# 3. Get the headers (includes User-Agent AND Client Hints)
headers = identity.get_headers()

# Use with requests/httpx
# response = requests.get("https://httpbin.org/headers", headers=headers)

print(f"Browser: {identity.meta_browser.value}")
print(f"OS:      {identity.meta_os.value}")
print(headers)
```

### Sample Output

```json
{
    "User-Agent": "Mozilla/5.0 (Linux; Android 15; CPH2371) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
    "Sec-CH-UA": "\"Google Chrome\";v=\"142\", \"Not)A(Brand\";v=\"24\", \"Chromium\";v=\"142\"",
    "Sec-CH-UA-Mobile": "?1",
    "Sec-CH-UA-Platform": "\"Android\"",
    "Sec-CH-UA-Full-Version-List": "\"Google Chrome\";v=\"142.0.7737.142\", \"Chromium\";v=\"142.0.7737.142\", \"Not:A;Brand\";v=\"24\""
}
```

---

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

---

## How it works

### The Data Sources

We don't guess. We utilize three distinct data layers:

1.  **`market_share.json`**: Global browser usage stats (Chrome, Safari, Edge, Firefox).
2.  **`os_distribution.json`**: The probability of an OS given a specific browser (e.g., Safari is 100% macOS/iOS, but Chrome is split between Windows, Mac, Linux, and Android).
3.  **`device_models.json`**: A curated list of ~500 real-world mobile device fingerprints.

### Version Expansion

Market data usually gives us "Chrome 142". We automatically expand this into valid, realistic build numbers (e.g., `142.0.4567.12`) using heuristic slopes to ensure the sub-versions look chronologically accurate.

---

## Maintenance & Updates

The browser ecosystem moves fast.
*   **Current Data Snapshot:** December 12, 2025.
*   **Next Scheduled Update:** Q1 2026.


## License

MIT License. Feel free to use this in your commercial scrapers, bots or testing suites.
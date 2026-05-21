# Android 10 User-Agent Reduction Fix

## Problem

The Chrome 110+ user-agent reduction was not correctly implemented. According to [Chrome's user-agent reduction specification](https://www.chromium.org/updates/ua-reduction), starting from Chrome 110 (February 2023), Chrome and other Chromium-based browsers should use a **fixed Android version (10) and fixed device model (K)** for user-agent strings.

### Before Fix

**Issue:** Only the device model was being fixed to "K", but the actual Android version from templates was still being used.

Example (INCORRECT):
```
Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36
                      ^^
                      Wrong: Should be "10", not "14"
```

### After Fix

**Correct:** Both Android version AND device model are fixed to standard values.

Example (CORRECT):
```
Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36
                      ^^
                      Correct: Fixed to "10"
```

## What Was Changed

**File:** `uaforge/core/generator.py` (lines 320-327)

### Code Changes

```python
# BEFORE (INCORRECT)
if hw_info.model and chromium_version >= 110:
    os_token = f"{os_token}; K"  # Only fixed model, kept actual Android version

# AFTER (CORRECT)
is_chromium = candidate.family in [BrowserFamily.CHROME, BrowserFamily.EDGE, BrowserFamily.OPERA]

if hw_info.model and is_chromium and chromium_version >= 110:
    # Chrome 110+ uses fixed Android 10 and model K for user-agent reduction
    os_token = "Linux; Android 10; K"  # Fixed both version and model
```

## Browser Behavior

### Chromium-Based Browsers (Chrome, Edge, Opera)
- **Version 110+:** Uses fixed `"Linux; Android 10; K"`
- **Version < 110:** Uses actual Android version and device model

Example for Chrome 144:
```
Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36
```

### Non-Chromium Browsers (Firefox, Safari)
- **All versions:** Uses actual Android version and device model
- **Not affected** by Chrome's user-agent reduction

Example for Firefox 147:
```
Mozilla/5.0 (Linux; Android 13; SM-G7102; rv:147.0.0.0) Gecko/20100101 Firefox/147.0.0.0
                      ^^       ^^^^^^^^^
                      Actual version and model (correct for Firefox)
```

## Test Results

All test scenarios pass:

✅ **Chrome on Android:** Correctly uses `"Android 10; K"`
✅ **Firefox on Android:** Correctly uses actual Android version (e.g., "13") and device model
✅ **Session consistency:** Same session produces identical user-agents across different generators
✅ **Deterministic generation:** Android 10 reduction applies correctly with session-based generation

## References

- [Chrome User-Agent Reduction](https://www.chromium.org/updates/ua-reduction)
- [User-Agent Client Hints Migration](https://web.dev/user-agent-client-hints/)
- Chrome 110 Release: February 2023

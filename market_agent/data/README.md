# about the data

just a quick breakdown of what these files do since they control how the stuff gets generated.

### `market_share.json`

basically the browser stats. lists things like chrome, safari, edge and their percentages. the script looks here first to pick which browser to fake based on how popular it is.

### `os_distribution.json`

this handles the OS logic. like if the script picks chrome, this file tells it "ok, make it 70% chance of windows, 20% mac", etc. also has the actual text snippets for the OS part of the user agent string.

### `device_models.json`

just a huge list of real phone models (samsung, pixel, xiaomi). we use this for mobile agents so the headers have actual hardware names in them to look legit.
from uaforge.core.generator import UserAgentGenerator
import json

from uaforge.models.enums import BrowserFamily
# 1. Initialize the generator
agent = UserAgentGenerator()
identity = agent.generate(realistic=True)
while identity.meta_browser != BrowserFamily.CHROME:
    identity = agent.generate()
headers = identity.get_headers()

print(json.dumps(headers, indent=0))

# 2. Get all client hints
all_client_hints = identity.get_all_client_hints()
print(json.dumps(all_client_hints, indent=0))
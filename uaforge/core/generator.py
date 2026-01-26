import random
from typing import Optional, Dict, Union

from ..data.loader import DataLoader, BrowserCandidate
from ..models.enums import BrowserFamily, DeviceType, OSType, EngineType
from ..models.objects import UserAgentData, BrowserInfo, OSInfo, HardwareInfo
from .versioning import VersionExpander
from .client_hints import ClientHintsGenerator
from .alias_sampler import AliasSampler


class UserAgentGenerator:
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed if seed is not None else 0  # Store base seed
        self.loader: DataLoader = DataLoader()
        self.rand: random.Random = random.Random(seed)
        self.candidate_sampler: AliasSampler = AliasSampler(self.loader.weights, self.rand)

        self._os_template_samplers: Dict[str, AliasSampler] = {}
        for os_key, templates in self.loader.os_dist_raw.get("os_templates", {}).items():
            if templates:
                weights = [t.get('probability', 1.0) for t in templates]
                self._os_template_samplers[os_key] = AliasSampler(weights, self.rand)

        self._os_choice_cache: Dict[tuple, Dict] = {}
        for candidate in self.loader.candidates:
            if candidate.device_type == DeviceType.MOBILE:
                if candidate.family == BrowserFamily.CHROME:
                    key = "and_chr"
                elif candidate.family == BrowserFamily.FIREFOX:
                    key = "and_ff"
                elif candidate.family == BrowserFamily.SAFARI:
                    key = "ios_saf"
                elif candidate.family == BrowserFamily.OPERA:
                    key = "op_mob"
                else:
                    key = "android"
                weight_key = "mobile_weights"
            else:
                key = candidate.family.value
                weight_key = "desktop_weights"

            cache_key = (key, weight_key)
            if cache_key not in self._os_choice_cache:
                choices, weights = self.loader.get_os_choices_and_weights(key, weight_key)
                if choices and weights:
                    self._os_choice_cache[cache_key] = {
                        'sampler': AliasSampler(weights, self.rand),
                        'choices': choices
                    }

        self._device_model_cache: Dict[str, list] = {
            "samsung": self.loader.get_device_models("samsung"),
            "google_pixel": self.loader.get_device_models("google_pixel"),
            "oppo_realme_generic": self.loader.get_device_models("oppo_realme_generic"),
            "xiaomi_ecosystem": self.loader.get_device_models("xiaomi_ecosystem")
        }

        self._ua_metadata: list = []
        for c in self.loader.candidates:
            self._ua_metadata.append({
                'family': c.family,
                'device': c.device_type,
                'version': c.version  # Safari marketing version
            })

    @staticmethod
    def _build_ua_string(family: BrowserFamily, device: DeviceType, os_token: str, full_version: str, marketing_version: str = None) -> str:
        """
        Build user agent string based on browser family and parameters.

        Args:
            family: Browser family
            device: Device type
            os_token: OS token string
            full_version: Full version string
            marketing_version: Marketing version for Safari

        Returns:
            Complete user agent string
        """
        if family == BrowserFamily.CHROME:
            mobile = 'Mobile ' if device == DeviceType.MOBILE else ''
            return (f"Mozilla/5.0 ({os_token}) AppleWebKit/537.36 (KHTML, like Gecko) "
                    f"Chrome/{full_version} {mobile}Safari/537.36")

        elif family == BrowserFamily.EDGE:
            return (f"Mozilla/5.0 ({os_token}) AppleWebKit/537.36 (KHTML, like Gecko) "
                    f"Chrome/{full_version} Safari/537.36 Edg/{full_version}")

        elif family == BrowserFamily.FIREFOX:
            return f"Mozilla/5.0 ({os_token}; rv:{full_version}) Gecko/20100101 Firefox/{full_version}"

        elif family == BrowserFamily.SAFARI:
            final_os_token = os_token.replace("{version}", marketing_version.replace('.', '_'))
            webkit_version = "605.1.15"
            return (f"Mozilla/5.0 ({final_os_token}) AppleWebKit/{webkit_version} (KHTML, like Gecko) "
                    f"Version/{marketing_version} Mobile/15E148 Safari/{webkit_version}")

        elif family == BrowserFamily.OPERA:
            chromium_major = int(full_version.split('.')[0]) + 16
            chromium_version = f"{chromium_major}.0.0.0"
            return (f"Mozilla/5.0 ({os_token}) AppleWebKit/537.36 (KHTML, like Gecko) "
                    f"Chrome/{chromium_version} Safari/537.36 OPR/{full_version}")

        else:  # Other Chromium-based
            return f"Mozilla/5.0 ({os_token}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{full_version} Safari/537.36"

    def _map_os_to_platform(self, os_type: OSType) -> str:
        """
        Map OSType enum to platform string for version lookup.

        Args:
            os_type: Operating system type enum

        Returns:
            Platform string ("windows", "macos", or "linux")
        """
        if os_type == OSType.WINDOWS:
            return "windows"
        elif os_type in (OSType.MACOS, OSType.IOS):
            return "macos"
        else:
            # Default to linux for Android and other OS types
            return "linux"

    def _resolve_os(self, candidate: BrowserCandidate, rand=None) -> Dict:
        """
        Decides which OS to use based on the browser candidate.
        Uses os_distribution.json templates to determine strings and platform versions.
        Uses cached samplers to avoid creating AliasSampler instances on every call.

        Args:
            candidate: Browser candidate
            rand: Optional random instance to use

        Returns:
            Dictionary with OS information
        """
        if rand is None:
            rand = self.rand
        # Determine cache key for OS selection based on device type and family
        if candidate.device_type == DeviceType.MOBILE:
            if candidate.family == BrowserFamily.CHROME:
                key = "and_chr"
            elif candidate.family == BrowserFamily.FIREFOX:
                key = "and_ff"
            elif candidate.family == BrowserFamily.SAFARI:
                key = "ios_saf"
            elif candidate.family == BrowserFamily.OPERA:
                key = "op_mob"
            else:
                key = "android"
            weight_key = "mobile_weights"
        else:
            key = candidate.family.value
            weight_key = "desktop_weights"

        # Look up cached sampler and choices
        cache_key = (key, weight_key)
        cached = self._os_choice_cache.get(cache_key)

        # Fallback if no cached data available
        if not cached:
            return {
                "type": OSType.LINUX,
                "platform_header": "Linux",
                "ua_token": "X11; Linux x86_64",
                "platform_version": "5.0.0"
            }

        # Use cached sampler to select OS configuration
        selected_os_config = cached['choices'][cached['sampler'].sample(rand=rand)]

        os_key = selected_os_config['os']
        platform_header = selected_os_config['platform']

        templates = self.loader.get_os_template(os_key)
        ua_token = "Unknown OS"
        pv = "0.0.0"

        if templates:
            template_sampler = self._os_template_samplers.get(os_key)
            if template_sampler:
                selected_template = templates[template_sampler.sample(rand=rand)]
            else:
                selected_template = rand.choice(templates)

            ua_token = selected_template['ua_token']

            if 'platform_version' in selected_template:
                pv = selected_template['platform_version']
            else:
                if os_key == "ios":
                    pv = f"{rand.randint(16,17)}.{rand.randint(0,5)}.0"
                elif os_key == "linux":
                    pv = f"{rand.randint(5,6)}.{rand.randint(4,19)}.0"
                else:
                    pv = "1.0.0"

        return {
            "type": OSType(os_key) if os_key in OSType._value2member_map_ else OSType.UNKNOWN,
            "platform_header": platform_header,
            "ua_token": ua_token,
            "platform_version": pv,
        }

    def _resolve_hardware(self, device_type: DeviceType, family: BrowserFamily, rand=None) -> HardwareInfo:
        """
        Resolve hardware information based on device type and browser family.

        Args:
            device_type: Device type
            family: Browser family
            rand: Optional random instance to use

        Returns:
            HardwareInfo object
        """
        if rand is None:
            rand = self.rand

        if device_type == DeviceType.DESKTOP:
            return HardwareInfo(device_type=DeviceType.DESKTOP, model=None, cpu_arch="x86_64")

        if family == BrowserFamily.SAFARI:
            return HardwareInfo(device_type=DeviceType.MOBILE, model="iPhone", brand_header_value='"iPhone";v="16"')
        elif family == BrowserFamily.CHROME and rand.random() < 0.3:
            model_list = self._device_model_cache.get("google_pixel", [])
        else:
            cats = ["samsung", "oppo_realme_generic", "xiaomi_ecosystem", "google_pixel"]
            cat = rand.choice(cats)
            model_list = self._device_model_cache.get(cat, [])

        if not model_list:
             return HardwareInfo(device_type=DeviceType.MOBILE, model="Generic Android", cpu_arch="arm64")

        selected_model = rand.choice(model_list)

        return HardwareInfo(
            device_type=DeviceType.MOBILE,
            model=selected_model,
            cpu_arch="arm64"
        )

    def _session_to_seed(self, session: Union[str, int, None]) -> Optional[int]:
        """
        Convert a session identifier to a deterministic seed.
        
        Args:
            session: Session identifier (string, int, or None)

        Returns:
            Deterministic seed derived from session, or None if session is None
        """
        if session is None:
            return None

        session_str = str(session)
        h = self.seed
        for char in session_str:
            h = (h * 31 + ord(char)) & 0x7FFFFFFF

        return h

    def generate(self, session: Union[str, int, None] = None) -> UserAgentData:
        """
        Generate a user agent identity.

        Args:
            session: Optional session identifier for deterministic generation.
                     Same session will always produce the same user agent.
                     If None, uses the generator's default random state.

        Returns:
            UserAgentData object containing user agent string and client hints
        """
        # Create session-specific random instance if session is provided
        if session is not None:
            session_seed = self._session_to_seed(session)
            session_rand = random.Random(session_seed)
        else:
            session_rand = self.rand

        # Sample browser candidate
        idx = self.candidate_sampler.sample(rand=session_rand)
        candidate = self.loader.candidates[idx]

        # OS & Platform - resolve first so we can use it for version generation
        os_data = self._resolve_os(candidate, rand=session_rand)

        # Map OSType to platform string for Chrome version lookup
        platform = self._map_os_to_platform(os_data['type'])

        # Generate version on-the-fly with platform information
        full_version = VersionExpander.generate_full_version(
            candidate.family,
            candidate.version,
            rand=session_rand,
            platform=platform,
            loader=self.loader
        )
        major_version = full_version.split('.', 1)[0]
        full_version_flattened = major_version + '.0.0.0'

        # get internal chromium version
        chromium_version = ClientHintsGenerator.get_major_chromium_full_version(
            candidate.family,
            full_version,
            rand=session_rand,
            loader=self.loader
        )

        # Hardware
        hw_info = self._resolve_hardware(candidate.device_type, candidate.family, rand=session_rand)

        # Construct UA String
        os_token = os_data['ua_token']

        # Android Model Injection
        if candidate.device_type == DeviceType.MOBILE and os_data['type'] == OSType.ANDROID:
            # Check if this is a Chromium-based browser
            is_chromium = candidate.family in [BrowserFamily.CHROME, BrowserFamily.EDGE, BrowserFamily.OPERA]

            if hw_info.model and is_chromium and chromium_version >= 110:
                # Chrome 110+ uses fixed Android 10 and model K for user-agent reduction
                # https://www.chromium.org/updates/ua-reduction
                os_token = "Linux; Android 10; K"
            elif hw_info.model:
                # Older Chrome versions or non-Chromium browsers include actual device model
                os_token = f"{os_token}; {hw_info.model}"

        # Build UA string using metadata
        metadata = self._ua_metadata[idx]
        ua_string = self._build_ua_string(
            metadata['family'],
            metadata['device'],
            os_token,
            full_version_flattened,
            metadata['version']  # Safari marketing version
        )
        
        # Handle Client Hints
        brands = ClientHintsGenerator.generate_brands(candidate.family, candidate.version, rand=session_rand)
        full_version_list = ClientHintsGenerator.generate_full_version_list(
            candidate.family,
            full_version,
            rand=session_rand,
            loader=self.loader
        )
        full_version_hint = ClientHintsGenerator.generate_full_version(candidate.family, full_version)
        if not brands:
            # Firefox/Safari do not send these headers
            ch_mobile = ""
            ch_platform = ""
            ch_platform_version = ""
            ch_model = ""
            ch_arch = ""
            ch_bitness = ""
            ch_full = ""
            ch_full_version = ""
            ch_form_factors = ""
            ch_wow64 = ""
            ch_prefers_color_scheme = ""
        else:
            ch_mobile = ClientHintsGenerator.get_mobile_token(candidate.device_type == DeviceType.MOBILE)
            ch_platform = os_data['platform_header']
            ch_platform_version = os_data['platform_version']
            ch_model = hw_info.model if candidate.device_type == DeviceType.MOBILE and hw_info.model else ""
            # Optimize: desktop is always x86_64, mobile is always arm64
            ch_arch = "arm" if candidate.device_type == DeviceType.MOBILE else "x86"
            ch_bitness = "64"
            ch_full = full_version_list
            ch_full_version = full_version_hint
            ch_form_factors = ClientHintsGenerator.generate_form_factors(candidate.device_type, rand=session_rand)
            ch_wow64 = ClientHintsGenerator.get_wow64_token(False)  # Assuming not WoW64 by default
            ch_prefers_color_scheme = ClientHintsGenerator.get_prefers_color_scheme(rand=session_rand)

        return UserAgentData(
            user_agent=ua_string,
            ch_brands=brands,
            ch_full_version_list=ch_full,
            ch_mobile=ch_mobile,
            ch_platform=ch_platform,
            ch_platform_version=ch_platform_version,
            ch_model=ch_model,
            ch_arch=ch_arch,
            ch_bitness=ch_bitness,
            ch_full_version=ch_full_version,
            ch_form_factors=ch_form_factors,
            ch_wow64=ch_wow64,
            ch_prefers_color_scheme=ch_prefers_color_scheme,
            meta_os=os_data['type'],
            meta_browser=candidate.family,
            meta_device=candidate.device_type
        )

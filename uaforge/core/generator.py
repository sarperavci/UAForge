import random
from typing import Optional, Dict

from ..data.loader import DataLoader, BrowserCandidate
from ..models.enums import BrowserFamily, DeviceType, OSType, EngineType
from ..models.objects import UserAgentData, BrowserInfo, OSInfo, HardwareInfo
from .versioning import VersionExpander
from .client_hints import ClientHintsGenerator
from .alias_sampler import AliasSampler


class UserAgentGenerator:
    def __init__(self, seed: Optional[int] = None, pool_size: int = 1000):
        self.loader = DataLoader()
        self.rand = random.Random(seed)
        self.candidate_sampler = AliasSampler(self.loader.weights, self.rand)
        
        self._version_pools = {}
        for candidate in self.loader.candidates:
            key = (candidate.family, candidate.version)
            if key not in self._version_pools:
                pool = []
                for _ in range(pool_size):
                    pool.append(VersionExpander.generate_full_version(candidate.family, candidate.version, rand=self.rand))
                self._version_pools[key] = pool
        
        self._os_template_samplers = {}
        for os_key, templates in self.loader.os_dist_raw.get("os_templates", {}).items():
            if templates:
                weights = [t.get('probability', 1.0) for t in templates]
                self._os_template_samplers[os_key] = AliasSampler(weights, self.rand)
        
        self._device_model_pools = {}
        for category in ["samsung", "google_pixel", "oppo_realme_generic", "xiaomi_ecosystem"]:
            models = self.loader.get_device_models(category)
            if models:
                pool_size = min(300, len(models))
                self._device_model_pools[category] = self.rand.choices(models, k=pool_size)
        
        self._os_samplers = []
        self._os_choices = []
        for candidate in self.loader.candidates:
            if candidate.device_type == DeviceType.MOBILE:
                if candidate.family == BrowserFamily.CHROME:
                    key = "and_chr"
                elif candidate.family == BrowserFamily.FIREFOX:
                    key = "and_ff"
                elif candidate.family == BrowserFamily.SAFARI:
                    key = "ios_saf"
                elif candidate.family == BrowserFamily.SAMSUNG:
                    key = "samsung"
                elif candidate.family == BrowserFamily.OPERA:
                    key = "op_mob"
                elif candidate.family == BrowserFamily.UC:
                    key = "and_uc"
                else:
                    key = "android"
                choices, weights = self.loader.get_os_choices_and_weights(key, "mobile_weights")
            else:
                key = candidate.family.value
                choices, weights = self.loader.get_os_choices_and_weights(key, "desktop_weights")
            
            if choices and weights:
                self._os_samplers.append(AliasSampler(weights, self.rand))
                self._os_choices.append(choices)
            else:
                self._os_samplers.append(None)
                self._os_choices.append(None)
        
        self._ua_builders = []
        for c in self.loader.candidates:
            fam = c.family
            device = c.device_type

            if fam == BrowserFamily.CHROME:
                def make_os_token_and_build(os_token, fv, device=device):
                    return (f"Mozilla/5.0 ({os_token}) AppleWebKit/537.36 (KHTML, like Gecko) "
                            f"Chrome/{fv} {('Mobile ' if device == DeviceType.MOBILE else '')}Safari/537.36")
            elif fam == BrowserFamily.EDGE:
                def make_os_token_and_build(os_token, fv, device=device):
                    return (f"Mozilla/5.0 ({os_token}) AppleWebKit/537.36 (KHTML, like Gecko) "
                            f"Chrome/{fv} Safari/537.36 Edg/{fv}")
            elif fam == BrowserFamily.FIREFOX:
                def make_os_token_and_build(os_token, fv, device=device):
                    return (f"Mozilla/5.0 ({os_token}; rv:{fv}) Gecko/20100101 Firefox/{fv}")
            elif fam == BrowserFamily.SAFARI:
                # safari will replace {version} within os token
                sv = c.version
                def make_os_token_and_build(os_token, fv, device=device, sv=sv):
                    final_os_token = os_token.replace("{version}", sv.replace('.', '_'))
                    webkit_version = "605.1.15"
                    return (f"Mozilla/5.0 ({final_os_token}) AppleWebKit/{webkit_version} (KHTML, like Gecko) "
                            f"Version/{sv} Mobile/15E148 Safari/{webkit_version}")
            else:
                def make_os_token_and_build(os_token, fv, device=device):
                    return f"Mozilla/5.0 ({os_token}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{fv} Safari/537.36"

            self._ua_builders.append(make_os_token_and_build)

    def _resolve_os(self, candidate_idx: int) -> Dict:
        """
        Decides which OS to use based on the browser candidate.
        Uses os_distribution.json templates to determine strings and platform versions.
        """
        # Use precomputed OS sampler for this candidate
        sampler = self._os_samplers[candidate_idx]
        choices = self._os_choices[candidate_idx]
        
        # Fallback
        if not sampler or not choices:
            return {
                "type": OSType.LINUX,
                "platform_header": "Linux", 
                "ua_token": "X11; Linux x86_64", 
                "platform_version": "5.0.0"
            }

        selected_os_config = choices[sampler.sample()]

        os_key = selected_os_config['os']
        platform_header = selected_os_config['platform']
        
        templates = self.loader.get_os_template(os_key)
        ua_token = "Unknown OS"
        pv = "0.0.0"

        if templates:
            sampler = self._os_template_samplers.get(os_key)
            if sampler:
                selected_template = templates[sampler.sample()]
            else:
                selected_template = self.rand.choice(templates)
            
            ua_token = selected_template['ua_token']
            
            if 'platform_version' in selected_template:
                pv = selected_template['platform_version']
            else:
                if os_key == "ios":
                    pv = f"{self.rand.randint(16,17)}.{self.rand.randint(0,5)}.0"
                elif os_key == "linux":
                    pv = f"{self.rand.randint(5,6)}.{self.rand.randint(4,19)}.0"
                else:
                    pv = "1.0.0"

        return {
            "type": OSType(os_key) if os_key in OSType._value2member_map_ else OSType.UNKNOWN,
            "platform_header": platform_header,
            "ua_token": ua_token,
            "platform_version": pv,
        }

    def _resolve_hardware(self, device_type: DeviceType, family: BrowserFamily) -> HardwareInfo:
        if device_type == DeviceType.DESKTOP:
            return HardwareInfo(device_type=DeviceType.DESKTOP, model=None, cpu_arch="x86_64")

        if family == BrowserFamily.SAMSUNG:
            model_list = self._device_model_pools.get("samsung", [])
        elif family == BrowserFamily.SAFARI:
            return HardwareInfo(device_type=DeviceType.MOBILE, model="iPhone", brand_header_value='"iPhone";v="16"')
        elif family == BrowserFamily.CHROME and self.rand.random() < 0.3:
            model_list = self._device_model_pools.get("google_pixel", [])
        else:
            cats = ["oppo_realme_generic", "xiaomi_ecosystem"]
            cat = self.rand.choice(cats)
            model_list = self._device_model_pools.get(cat, [])

        if not model_list:
             return HardwareInfo(device_type=DeviceType.MOBILE, model="Generic Android", cpu_arch="arm64")

        selected_model = self.rand.choice(model_list)

        return HardwareInfo(
            device_type=DeviceType.MOBILE,
            model=selected_model,
            cpu_arch="arm64"
        )

    def generate(self) -> UserAgentData:
        idx = self.candidate_sampler.sample()
        candidate = self.loader.candidates[idx]
        version_pool = self._version_pools.get((candidate.family, candidate.version))
        full_version = self.rand.choice(version_pool) if version_pool else VersionExpander.generate_full_version(candidate.family, candidate.version, rand=self.rand)
        full_version_flattened = full_version.split('.', 1)[0] + '.0.0.0'
        
        # OS & Platform
        os_data = self._resolve_os(idx)

        # Hardware
        hw_info = self._resolve_hardware(candidate.device_type, candidate.family)

        # Construct UA String
        os_token = os_data['ua_token']
        
        # Android Model Injection
        if candidate.device_type == DeviceType.MOBILE and os_data['type'] == OSType.ANDROID:
            if hw_info.model:
                # ua_token from JSON is "Linux; Android 14"
                # We append the model: "Linux; Android 14; SM-S918B"
                os_token = f"{os_token}; {hw_info.model}"

        # Use precomputed builder for this candidate to assemble UA string quickly
        ua_string = self._ua_builders[idx](os_token, full_version_flattened)
        
        # Handle Client Hints
        brands = ClientHintsGenerator.generate_brands(candidate.family, candidate.version, rand=self.rand)
        full_version_list = ClientHintsGenerator.generate_full_version_list(candidate.family, full_version, rand=self.rand)

        if not brands:
            # Firefox/Safari do not send these headers
            ch_mobile = ""
            ch_platform = ""
            ch_platform_version = ""
            ch_model = ""
            ch_arch = ""
            ch_bitness = ""
            ch_full = ""
        else:
            ch_mobile = ClientHintsGenerator.get_mobile_token(candidate.device_type == DeviceType.MOBILE)
            ch_platform = os_data['platform_header']
            ch_platform_version = os_data['platform_version']
            ch_model = hw_info.model if candidate.device_type == DeviceType.MOBILE and hw_info.model else ""
            ch_arch = "x86" if "x86" in hw_info.cpu_arch else "arm"
            ch_bitness = "64"
            ch_full = full_version_list

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
            meta_os=os_data['type'],
            meta_browser=candidate.family,
            meta_device=candidate.device_type
        )

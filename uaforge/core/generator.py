import random
from typing import Optional, Dict

from ..data.loader import DataLoader, BrowserCandidate
from ..models.enums import BrowserFamily, DeviceType, OSType, EngineType
from ..models.objects import UserAgentData, BrowserInfo, OSInfo, HardwareInfo
from .versioning import VersionExpander
from .client_hints import ClientHintsGenerator


class UserAgentGenerator:
    def __init__(self, seed: Optional[int] = None):
        self.loader = DataLoader()
        if seed is not None:
            random.seed(seed)

    def _resolve_os(self, candidate: BrowserCandidate) -> Dict:
        """
        Decides which OS to use based on the browser candidate.
        Uses os_distribution.json templates to determine strings and platform versions.
        """
        weights_list = []
        
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
            weights_list = self.loader.os_dist_raw.get("mobile_weights", {}).get(key, [])
        else:
            key = candidate.family.value
            weights_list = self.loader.os_dist_raw.get("desktop_weights", {}).get(key, [])

        # Fallback
        if not weights_list:
            return {
                "type": OSType.LINUX,
                "platform_header": "Linux", 
                "ua_token": "X11; Linux x86_64", 
                "platform_version": "5.0.0"
            }

        choices = weights_list
        weights = [x['weight'] for x in choices]
        selected_os_config = random.choices(choices, weights=weights, k=1)[0]

        os_key = selected_os_config['os']
        platform_header = selected_os_config['platform']
        
        templates = self.loader.get_os_template(os_key)
        ua_token = "Unknown OS"
        pv = "0.0.0"

        if templates:
            t_weights = [t.get('probability', 1.0) for t in templates]
            selected_template =  random.choices(templates, weights=t_weights, k=1)[0]
            
            ua_token = selected_template['ua_token']
            
            if 'platform_version' in selected_template:
                pv = selected_template['platform_version']
            else:
                if os_key == "ios":
                    pv = f"{random.randint(16,17)}.{random.randint(0,5)}.0"
                elif os_key == "linux":
                    pv = f"{random.randint(5,6)}.{random.randint(4,19)}.0"
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

        model_list = []
        if family == BrowserFamily.SAMSUNG:
            model_list = self.loader.get_device_models("samsung")
        elif family == BrowserFamily.SAFARI:
            return HardwareInfo(device_type=DeviceType.MOBILE, model="iPhone", brand_header_value='"iPhone";v="16"')
        elif family == BrowserFamily.CHROME and random.random() < 0.3:
            model_list = self.loader.get_device_models("google_pixel")
        else:
            cats = ["oppo_realme_generic", "xiaomi_ecosystem"]
            cat = random.choice(cats)
            model_list = self.loader.get_device_models(cat)

        if not model_list:
             return HardwareInfo(device_type=DeviceType.MOBILE, model="Generic Android", cpu_arch="arm64")

        selected_model = random.choice(model_list)

        return HardwareInfo(
            device_type=DeviceType.MOBILE,
            model=selected_model,
            cpu_arch="arm64"
        )

    def generate(self) -> UserAgentData:
        candidate = random.choices(self.loader.candidates, weights=self.loader.weights, k=1)[0]

        full_version = VersionExpander.generate_full_version(candidate.family, candidate.version)
        # flatten to major version for UA string
        full_version_flattened = full_version.split('.', 1)[0] + '.0.0.0'
        
        # OS & Platform
        os_data = self._resolve_os(candidate)

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

        ua_string = ""
        if candidate.family == BrowserFamily.CHROME:
            ua_string = (f"Mozilla/5.0 ({os_token}) AppleWebKit/537.36 (KHTML, like Gecko) "
                         f"Chrome/{full_version_flattened} {('Mobile ' if candidate.device_type == DeviceType.MOBILE else '')}Safari/537.36")
        elif candidate.family == BrowserFamily.EDGE:
            ua_string = (f"Mozilla/5.0 ({os_token}) AppleWebKit/537.36 (KHTML, like Gecko) "
                         f"Chrome/{full_version_flattened} Safari/537.36 Edg/{full_version_flattened}")
        elif candidate.family == BrowserFamily.FIREFOX:
            rv_version = full_version 
            ua_string = (f"Mozilla/5.0 ({os_token}; rv:{rv_version}) Gecko/20100101 Firefox/{full_version}")
        elif candidate.family == BrowserFamily.SAFARI:
            safari_version = candidate.version
            webkit_version = "605.1.15"
            # Simple template replacement for iOS version
            final_os_token = os_token.replace("{version}", safari_version.replace(".", "_"))
            ua_string = (f"Mozilla/5.0 ({final_os_token}) AppleWebKit/{webkit_version} (KHTML, like Gecko) "
                         f"Version/{safari_version} Mobile/15E148 Safari/{webkit_version}")
        else:
             ua_string = f"Mozilla/5.0 ({os_token}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{full_version} Safari/537.36"
        
        # Handle Client Hints
        brands = ClientHintsGenerator.generate_brands(candidate.family, candidate.version)
        full_version_list = ClientHintsGenerator.generate_full_version_list(candidate.family, full_version)

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

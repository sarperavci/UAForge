import json
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .mappings import MARKET_KEY_MAP
from ..models.enums import BrowserFamily, DeviceType, OSType
from ..exceptions import DataLoadError
from ..core.alias_sampler import AliasSampler


@dataclass
class BrowserCandidate:
    """
    An internal representation of a specific browser version and its weight.
    """
    family: BrowserFamily
    version: str
    device_type: DeviceType
    os_restriction: OSType # If distinct from UNKNOWN, this candidate enforces this OS
    share: float


class DataLoader:
    _instance = None
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._loaded:
            self.base_path = Path(__file__).parent
            
            # Raw Data Containers
            self.market_raw: Dict[str, Any] = {}
            self.os_dist_raw: Dict[str, Any] = {}
            self.device_models_raw: Dict[str, List[str]] = {}
            
            self.candidates: List[BrowserCandidate] = []
            self.weights: List[float] = []
            
            self._load_data()
            self._process_market_share()
            # Precompute OS weight caches for faster sampling
            self._os_weight_cache = {}
            self._os_alias_samplers = {}
            for scope in ("mobile_weights", "desktop_weights"):
                self._os_weight_cache[scope] = {}
                self._os_alias_samplers[scope] = {}
                for key, choices in self.os_dist_raw.get(scope, {}).items():
                    weights = [x.get('weight', 0.0) for x in choices]
                    self._os_weight_cache[scope][key] = (choices, weights)
                    if weights:
                        self._os_alias_samplers[scope][key] = weights  # store raw weights
            self._loaded = True

    def _load_data(self):
        """Loads JSON files from disk."""
        try:
            with open(self.base_path / "market_share.json", "r", encoding="utf-8") as f:
                self.market_raw = json.load(f)
            with open(self.base_path / "os_distribution.json", "r", encoding="utf-8") as f:
                self.os_dist_raw = json.load(f)
            with open(self.base_path / "device_models.json", "r", encoding="utf-8") as f:
                self.device_models_raw = json.load(f)
        except FileNotFoundError as e:
            raise DataLoadError(f"Critical data file missing: {e.filename}")
        except json.JSONDecodeError as e:
            raise DataLoadError(f"Corrupt JSON data: {e}")

    def _process_market_share(self):
        """
        Flattens the nested market_share.json into a single list of weighted candidates.
        """
        candidates = []
        weights = []
        
        # Iterate over keys like "chrome", "ios_saf"
        for key, versions in self.market_raw.items():
            if key not in MARKET_KEY_MAP:
                continue # Skip unknown keys or safe-guard against bad data

            family, default_device, os_restriction = MARKET_KEY_MAP[key]

            for entry in versions:
                version = entry.get("version")
                share = entry.get("global_share", 0.0)

                if share <= 0:
                    continue

                candidates.append(
                    BrowserCandidate(
                        family=family,
                        version=version,
                        device_type=default_device,
                        os_restriction=os_restriction,
                        share=share
                    )
                )
                weights.append(share)

        self.candidates = candidates
        self.weights = weights
        
        # Validate that we have data
        if not self.candidates:
            raise DataLoadError("No valid browser candidates found in market_share.json")

    def get_os_weights(self, browser_family: BrowserFamily, device_type: DeviceType) -> List[Dict]:
        """
        Retrieves OS distribution logic for a specific browser.
        e.g. Chrome Desktop -> Windows 70%, Mac 20%...
        """
        # Map enum to JSON keys used in os_distribution.json
        family_key = browser_family.value # e.g. "chrome"
        
        if device_type == DeviceType.DESKTOP:
            return self.os_dist_raw.get("desktop_weights", {}).get(family_key, [])
        elif device_type == DeviceType.MOBILE:
            return self.os_dist_raw.get("mobile_weights", {}).get(family_key, [])
        
        return []

    def get_device_models(self, category_key: str) -> List[str]:
        """Returns list of device models (e.g. for 'samsung' or 'google_pixel')"""
        return self.device_models_raw.get(category_key, [])

    def get_os_choices_and_weights(self, family_key: str, scope: str):
        """Return (choices, weights) for a given family_key and scope ('mobile_weights'|'desktop_weights')."""
        return self._os_weight_cache.get(scope, {}).get(family_key, ([], []))
    
    def get_os_weights_for_sampler(self, family_key: str, scope: str):
        """Return raw weights for building an alias sampler."""
        return self._os_alias_samplers.get(scope, {}).get(family_key, [])

    def get_os_template(self, os_key: str) -> List[Dict]:
        """Returns the template list for a specific OS (windows, linux)"""
        return self.os_dist_raw.get("os_templates", {}).get(os_key, [])

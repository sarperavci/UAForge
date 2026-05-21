import random

from uaforge.data.loader import DataLoader, BrowserCandidate
from uaforge.models.enums import BrowserFamily, DeviceType


def test_dataloader_loads_candidates() -> None:
    loader = DataLoader()
    assert len(loader.candidates) > 0
    assert len(loader.candidates) == len(loader.weights)


def test_sampling_returns_candidate() -> None:
    loader = DataLoader()
    choice = random.choices(loader.candidates, weights=loader.weights, k=1)[0]
    assert isinstance(choice, BrowserCandidate)


def test_get_os_weights_desktop_chrome() -> None:
    loader = DataLoader()
    weights = loader.get_os_weights(BrowserFamily.CHROME, DeviceType.DESKTOP)
    assert isinstance(weights, list)
    assert any(item.get("os") == "windows" for item in weights)


def test_dataloader_singleton() -> None:
    a = DataLoader()
    b = DataLoader()
    assert a is b


def test_device_specs_loaded() -> None:
    """Test that android_device_specs.json is loaded correctly."""
    loader = DataLoader()
    # Check that we have device specs for all major brands
    assert len(loader.get_all_device_specs("samsung")) > 0
    assert len(loader.get_all_device_specs("google_pixel")) > 0
    assert len(loader.get_all_device_specs("xiaomi_ecosystem")) > 0
    assert len(loader.get_all_device_specs("oppo_realme_generic")) > 0


def test_device_compatibility_filtering() -> None:
    """Test that device compatibility filtering works correctly."""
    loader = DataLoader()

    # Pixel 9 should be compatible with API 35 (Android 15)
    pixel_35 = loader.get_compatible_devices("google_pixel", 35)
    pixel_9_found = any(d.model_code == "Pixel 9" for d in pixel_35)
    assert pixel_9_found, "Pixel 9 should be compatible with API 35"

    # Pixel 2 should NOT be compatible with API 33 (max is 30)
    pixel_33 = loader.get_compatible_devices("google_pixel", 33)
    pixel_2_found = any(d.model_code == "Pixel 2" for d in pixel_33)
    assert not pixel_2_found, "Pixel 2 should NOT be compatible with API 33"

    # SM-G530H (Galaxy Grand Prime) should NOT be compatible with API 33
    samsung_33 = loader.get_compatible_devices("samsung", 33)
    g530h_found = any(d.model_code == "SM-G530H" for d in samsung_33)
    assert not g530h_found, "SM-G530H should NOT be compatible with API 33"


def test_weighted_device_sampling() -> None: 
    """Test that weighted device sampling returns compatible devices."""
    loader = DataLoader()
    rand = random.Random(42)

    # Sample a device compatible with API 33
    device = loader.sample_compatible_device("google_pixel", 33, rand)
    assert device is not None
    assert device.min_android_api <= 33 <= device.max_android_api

    # Sample from Samsung for API 30
    device = loader.sample_compatible_device("samsung", 30, rand)
    assert device is not None
    assert device.min_android_api <= 30 <= device.max_android_api

import random

from uaforge.data.loader import DataLoader, BrowserCandidate
from uaforge.models.enums import BrowserFamily, DeviceType


def test_dataloader_loads_candidates():
    loader = DataLoader()
    assert len(loader.candidates) > 0
    assert len(loader.candidates) == len(loader.weights)


def test_sampling_returns_candidate():
    loader = DataLoader()
    choice = random.choices(loader.candidates, weights=loader.weights, k=1)[0]
    assert isinstance(choice, BrowserCandidate)


def test_get_os_weights_desktop_chrome():
    loader = DataLoader()
    weights = loader.get_os_weights(BrowserFamily.CHROME, DeviceType.DESKTOP)
    assert isinstance(weights, list)
    assert any(item.get("os") == "windows" for item in weights)


def test_dataloader_singleton():
    a = DataLoader()
    b = DataLoader()
    assert a is b

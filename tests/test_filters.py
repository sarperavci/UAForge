import pytest

from uaforge.core.generator import UserAgentGenerator, _coerce_set
from uaforge.models.enums import BrowserFamily, DeviceType


@pytest.fixture(scope="module")
def gen():
    return UserAgentGenerator(seed=42)


def test_coerce_accepts_none():
    assert _coerce_set(None, BrowserFamily) is None


def test_coerce_accepts_single_enum():
    s = _coerce_set(BrowserFamily.CHROME, BrowserFamily)
    assert s == frozenset({BrowserFamily.CHROME})


def test_coerce_accepts_single_string():
    s = _coerce_set("chrome", BrowserFamily)
    assert s == frozenset({BrowserFamily.CHROME})


def test_coerce_accepts_iterable_mixed():
    s = _coerce_set(["chrome", BrowserFamily.FIREFOX], BrowserFamily)
    assert s == frozenset({BrowserFamily.CHROME, BrowserFamily.FIREFOX})


def test_coerce_rejects_invalid_value():
    with pytest.raises(ValueError):
        _coerce_set("not-a-browser", BrowserFamily)


def test_filter_to_chrome_desktop_only(gen):
    for _ in range(50):
        ua = gen.generate(families="chrome", device_types="desktop")
        assert ua.meta_browser == BrowserFamily.CHROME
        assert ua.meta_device == DeviceType.DESKTOP


def test_filter_to_chrome_only(gen):
    seen_devices = set()
    for _ in range(80):
        ua = gen.generate(families=BrowserFamily.CHROME)
        assert ua.meta_browser == BrowserFamily.CHROME
        seen_devices.add(ua.meta_device)
    assert len(seen_devices) >= 2


def test_filter_to_desktop_only(gen):
    seen_families = set()
    for _ in range(80):
        ua = gen.generate(device_types="desktop")
        assert ua.meta_device == DeviceType.DESKTOP
        seen_families.add(ua.meta_browser)
    assert len(seen_families) >= 2


def test_filter_multiple_families(gen):
    allowed = {BrowserFamily.CHROME, BrowserFamily.FIREFOX}
    seen = set()
    for _ in range(60):
        ua = gen.generate(families=["chrome", "firefox"])
        assert ua.meta_browser in allowed
        seen.add(ua.meta_browser)
    assert seen == allowed


def test_filter_empty_match_raises(gen):
    with pytest.raises(ValueError, match="no candidate"):
        gen.generate(families="chrome", device_types="mobile",
                     min_chromium_version=99999)


def test_filter_unweighted_still_respects(gen):
    for _ in range(30):
        ua = gen.generate(families="chrome", device_types="desktop",
                          weighted=False)
        assert ua.meta_browser == BrowserFamily.CHROME
        assert ua.meta_device == DeviceType.DESKTOP


def test_no_filter_yields_all_families_over_time(gen):
    seen = set()
    for _ in range(200):
        ua = gen.generate()
        seen.add(ua.meta_browser)
    assert len(seen) >= 3

import unittest
from uaforge.core.generator import UserAgentGenerator
from uaforge.models.enums import DeviceType, OSType, BrowserFamily


class TestGenerator(unittest.TestCase):

    def setUp(self):
        self.ua_gen = UserAgentGenerator()

    def test_determinism(self):
        """
        Enterprise Requirement: Same seed = Same UA.
        """
        seed_val = 12345
        gen1 = UserAgentGenerator(seed=seed_val)
        result1 = gen1.generate()

        gen2 = UserAgentGenerator(seed=seed_val)
        result2 = gen2.generate()

        self.assertEqual(result1.user_agent, result2.user_agent)
        self.assertEqual(result1.ch_brands, result2.ch_brands)
        self.assertEqual(result1.ch_platform, result2.ch_platform)

    def test_consistency_mobile(self):
        """
        If we get a Mobile UA, headers must say Mobile.
        """
        for _ in range(50):
            ua_data = self.ua_gen.generate()
            if ua_data.meta_device == DeviceType.MOBILE:
                # Some browsers (Firefox/Safari) intentionally do not send client hints.
                if ua_data.meta_browser in (BrowserFamily.FIREFOX, BrowserFamily.SAFARI):
                    self.assertEqual(ua_data.ch_mobile, "")
                else:
                    self.assertEqual(ua_data.ch_mobile, "?1", "Mobile header must be ?1")
                if ua_data.ch_platform and "Android" in ua_data.ch_platform:
                    self.assertIn("Android", ua_data.user_agent)
                return

    def test_consistency_desktop(self):
        """
        If we get a Desktop UA, headers must NOT say Mobile.
        """
        for _ in range(50):
            ua_data = self.ua_gen.generate()
            if ua_data.meta_device == DeviceType.DESKTOP:
                if ua_data.meta_browser in (BrowserFamily.FIREFOX, BrowserFamily.SAFARI):
                    self.assertEqual(ua_data.ch_mobile, "")
                else:
                    self.assertEqual(ua_data.ch_mobile, "?0")
                return

    def test_no_client_hints_for_firefox_safari(self):
        """
        Ensure Firefox and Safari do not produce Sec-CH-UA headers.
        """
        for _ in range(200):
            ua_data = self.ua_gen.generate()
            if ua_data.meta_browser in (BrowserFamily.FIREFOX, BrowserFamily.SAFARI):
                headers = ua_data.get_headers()
                self.assertNotIn("Sec-CH-UA", headers)
                self.assertEqual(ua_data.ch_brands, "")
                return
        self.skipTest("No Firefox or Safari UA found in 200 samples; try increasing samples if flaky")


if __name__ == '__main__':
    unittest.main()

import unittest
from uaforge.models.enums import BrowserFamily
from uaforge.core.versioning import VersionExpander
from uaforge.core.client_hints import ClientHintsGenerator


class TestCoreLogic(unittest.TestCase):
    
    def test_version_expander_simplified(self):
        """
        Verifies the new realistic versioning logic.
        """
        # Test Chrome/Chromium behavior
        ver = VersionExpander.generate_full_version(BrowserFamily.CHROME, "142")
        print(ver)
        # Should be e.g. 142.0.7722.181 (major.minor.build.patch) and major matches input
        self.assertRegex(ver, r'^142\.\d+\.\d+\.\d+$', "Chrome should be 'major.minor.build.patch' and start with the given major version")
      
        # Test Firefox behavior
        ver = VersionExpander.generate_full_version(BrowserFamily.FIREFOX, "115")
        self.assertEqual(ver, "115.0", "Firefox should be Major.0")

        # Test Safari behavior
        ver = VersionExpander.generate_full_version(BrowserFamily.SAFARI, "17.2")
        self.assertEqual(ver, "17.2", "Safari should pass through marketing version")

    def test_client_hints_grease(self):
        """
        Verifies that GREASE (fake brands) are generated and formatted correctly.
        """
        header = ClientHintsGenerator.generate_brands(BrowserFamily.CHROME, "120")
        # 1. Should be a string
        self.assertIsInstance(header, str)
        # 2. Should contain standard Chrome brands
        self.assertIn('"Chromium";v="120"', header)
        self.assertIn('"Google Chrome";v="120"', header)
        # 3. Should contain a GREASE brand (randomized, but check formatting)
        parts = header.split(", ")
        self.assertEqual(len(parts), 3, "Chrome should have 3 brands (1 Grease, 2 Real)")

    def test_client_hints_exclusion(self):
        # Firefox and Safari must get empty strings for brands and full version list
        self.assertEqual(ClientHintsGenerator.generate_brands(BrowserFamily.FIREFOX, "120"), "")
        self.assertEqual(ClientHintsGenerator.generate_brands(BrowserFamily.SAFARI, "120"), "")
        self.assertEqual(ClientHintsGenerator.generate_full_version_list(BrowserFamily.FIREFOX, "120.0.0.0"), "")
        self.assertEqual(ClientHintsGenerator.generate_full_version_list(BrowserFamily.SAFARI, "17.2"), "")


if __name__ == '__main__':
    unittest.main()

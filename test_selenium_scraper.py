import unittest
from unittest.mock import patch

from selenium_scraper import YieldScraper


class VanguardYieldTest(unittest.TestCase):
    @patch("selenium_scraper.urlopen")
    def test_gets_sec_yield_from_vanguard_api(self, get):
        get.return_value.__enter__.return_value.read.return_value = (
            b'{"dashboard":{"secYield":"3.70%"}}'
        )
        scraper = YieldScraper.__new__(YieldScraper)
        scraper.timeout = 10

        self.assertEqual(scraper.get_sec_yield("vusxx"), 3.70)
        get.assert_called_once_with(
            "https://investor.vanguard.com/irr/funds/profile/VUSXX", timeout=10
        )


if __name__ == "__main__":
    unittest.main()

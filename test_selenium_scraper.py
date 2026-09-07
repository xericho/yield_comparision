import unittest

from bs4 import BeautifulSoup

from selenium_scraper import YieldScraper


class VanguardYieldTest(unittest.TestCase):
    def test_extracts_sec_yield_from_vanguard_api_response(self):
        soup = BeautifulSoup(
            '<pre>{"dashboard":{"secYield":"3.70%"}}</pre>', "html.parser"
        )

        self.assertEqual(YieldScraper._extract_sec_yield_from_soup(None, soup), 3.70)

        soup = BeautifulSoup(
            '<pre>{"dashboard":{"secYield":"30.00%"}}</pre>', "html.parser"
        )
        self.assertIsNone(YieldScraper._extract_sec_yield_from_soup(None, soup))


if __name__ == "__main__":
    unittest.main()

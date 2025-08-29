"""Scraper for Vanguard SEC yields using headless Selenium."""

import time
import re
from typing import Optional, Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import platform


class VanguardScraper:
    """Scraper for Vanguard mutual fund SEC yields."""

    def __init__(self, headless: bool = True, timeout: int = 10):
        """Initialize the scraper.

        Parameters
        ----------
        headless : bool
            Whether to run Chrome in headless mode
        timeout : int
            Timeout in seconds for page loads and element waits
        """
        self.timeout = timeout
        if platform.system() == "Linux":
            from setup_selenium_driver import driver

            self.driver = driver
        else:
            self.driver = self._setup_driver(headless)

    def _setup_driver(self, headless: bool) -> webdriver.Chrome:
        """Set up Chrome driver with appropriate options."""
        chrome_options = Options()

        if headless:
            chrome_options.add_argument("--headless")

        # Additional options for better compatibility
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        # chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        # Disable images for faster loading
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")

        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )

    def get_sec_yield(self, symbol: str) -> Optional[float]:
        """Get SEC yield for a given Vanguard fund symbol.

        Parameters
        ----------
        symbol : str
            Fund symbol (e.g., 'vusxx', 'vctxx')

        Returns
        -------
        Optional[float]
            SEC yield as percentage (e.g., 4.24 for 4.24%), or None if not found
        """
        url = f"https://investor.vanguard.com/investment-products/mutual-funds/profile/{symbol.lower()}"

        try:
            print(f"Fetching {symbol.upper()} from {url}...")
            self.driver.get(url)

            # Wait for page to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Additional wait for dynamic content
            time.sleep(2)

            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Strategy 1: Look for SEC yield in various possible locations
            sec_yield = self._extract_sec_yield_from_soup(soup)

            if sec_yield is not None:
                print(f"✅ Found SEC yield for {symbol.upper()}: {sec_yield}%")
                return sec_yield

            # Strategy 2: Look for yield information in tables or data sections
            sec_yield = self._extract_from_performance_data(soup)

            if sec_yield is not None:
                print(f"✅ Found SEC yield for {symbol.upper()}: {sec_yield}%")
                return sec_yield

            print(f"❌ SEC yield not found for {symbol.upper()}")
            return None

        except TimeoutException:
            print(f"Timeout loading page for {symbol.upper()}")
            return None
        except Exception as e:
            print(f"Error scraping {symbol.upper()}: {str(e)}")
            return None

    def _extract_sec_yield_from_soup(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract SEC yield using various text patterns."""

        # Common patterns for SEC yield
        patterns = [
            r"SEC yield[:\s]*(\d+\.?\d*)\s*%",
            r"SEC\s+yield[:\s]*(\d+\.?\d*)\s*%",
            r"30-day SEC yield[:\s]*(\d+\.?\d*)\s*%",
            r"Yield[:\s]*(\d+\.?\d*)\s*%",
        ]

        # Get all text content
        text = soup.get_text()

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    yield_value = float(match.group(1))
                    # Sanity check: yield should be reasonable (0-20%)
                    if 0 <= yield_value <= 20:
                        return yield_value
                except (ValueError, IndexError):
                    continue

        return None

    def _extract_from_performance_data(self, soup: BeautifulSoup) -> Optional[float]:
        """Try to extract SEC yield from performance tables or data sections."""

        # Look for tables or divs that might contain yield data
        potential_containers = soup.find_all(
            ["table", "div", "section"],
            string=re.compile(r"yield|performance", re.IGNORECASE),
        )

        for container in potential_containers:
            # Look for parent elements that might contain the data
            parent = container.find_parent()
            if parent:
                text = parent.get_text()
                # Look for percentage values near yield mentions
                yield_match = re.search(r"(\d+\.?\d*)\s*%", text)
                if yield_match:
                    try:
                        yield_value = float(yield_match.group(1))
                        if 0 <= yield_value <= 20:
                            return yield_value
                    except ValueError:
                        continue

        return None

    def get_multiple_yields(self, symbols: list) -> Dict[str, Optional[float]]:
        """Get SEC yields for multiple symbols.

        Parameters
        ----------
        symbols : list
            List of fund symbols

        Returns
        -------
        Dict[str, Optional[float]]
            Dictionary mapping symbols to their SEC yields
        """
        results = {}
        for symbol in symbols:
            results[symbol.upper()] = self.get_sec_yield(symbol)
            # Small delay between requests to be respectful
            time.sleep(1)

        return results

    def close(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """Example usage."""
    symbols = ["vusxx", "vctxx"]  # Add more symbols as needed

    with VanguardScraper(headless=True) as scraper:
        yields = scraper.get_multiple_yields(symbols)

        print("\nScraping Results:")
        print("-" * 30)
        for symbol, yield_value in yields.items():
            if yield_value is not None:
                print(f"{symbol}: {yield_value}%")
            else:
                print(f"{symbol}: Not found")


if __name__ == "__main__":
    main()

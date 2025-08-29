"""Scraper for Ally Bank APY using headless Selenium."""

from sys import platform
import time
import re
from typing import Optional
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


class AllyScraper:
    """Scraper for Ally Bank online savings account APY."""

    def __init__(self, headless: bool = True, timeout: int = 15):
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

    def _setup_driver(self, headless: bool = True) -> webdriver.Chrome:
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

    def get_apy(self) -> Optional[float]:
        """Get APY for Ally Bank online savings account.

        Returns
        -------
        Optional[float]
            APY as percentage (e.g., 4.20 for 4.20%), or None if not found
        """
        url = "https://www.ally.com/bank/online-savings-account/"

        try:
            print(f"Fetching Ally Bank APY from {url}")
            self.driver.get(url)

            # Wait for page to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Additional wait for dynamic content to load
            time.sleep(3)

            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Strategy 1: Look for APY in various text patterns
            apy = self._extract_apy_from_text(soup)
            if apy is not None:
                print(f"✅ Found Ally Bank APY: {apy}%")
                return apy

            # Strategy 2: Look for APY in specific elements or data attributes
            apy = self._extract_apy_from_elements(soup)
            if apy is not None:
                print(f"✅ Found Ally Bank APY: {apy}%")
                return apy

            # Strategy 3: Look for rate information in tables or structured data
            apy = self._extract_apy_from_structured_data(soup)
            if apy is not None:
                print(f"✅ Found Ally Bank APY: {apy}%")
                return apy

            print("❌ Ally Bank APY not found")
            return None

        except TimeoutException:
            print("Timeout loading Ally Bank page")
            return None
        except Exception as e:
            print(f"Error scraping Ally Bank APY: {str(e)}")
            return None

    def _extract_apy_from_text(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract APY using various text patterns."""

        # Get all text content
        text = soup.get_text()

        # Common patterns for APY - more specific patterns first
        patterns = [
            r"APY[:\s]*(\d+\.?\d*)\s*%",
            r"Annual Percentage Yield[:\s]*(\d+\.?\d*)\s*%",
            r"(\d+\.?\d*)\s*%\s*APY",
            r"rate[:\s]*(\d+\.?\d*)\s*%",
            r"earn[:\s]*(\d+\.?\d*)\s*%",
            r"(\d+\.?\d*)\s*%\s*annual",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    apy_value = float(match.group(1))
                    # Sanity check: APY should be reasonable (0-10% for savings accounts)
                    if 0 <= apy_value <= 10:
                        return apy_value
                except (ValueError, IndexError):
                    continue

        return None

    def _extract_apy_from_elements(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract APY from specific HTML elements."""

        # Look for elements that commonly contain rate information
        selectors = [
            "[data-apy]",
            "[data-rate]",
            ".apy",
            ".rate",
            ".interest-rate",
            ".savings-rate",
            ".percentage",
            "[class*='apy']",
            "[class*='rate']",
            "[id*='apy']",
            "[id*='rate']",
        ]

        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                # Check data attributes
                for attr in ["data-apy", "data-rate", "data-percentage"]:
                    if element.has_attr(attr):
                        try:
                            apy_value = float(element[attr])
                            if 0 <= apy_value <= 10:
                                return apy_value
                        except (ValueError, TypeError):
                            continue

                # Check element text
                text = element.get_text(strip=True)
                match = re.search(r"(\d+\.?\d*)\s*%?", text)
                if match:
                    try:
                        apy_value = float(match.group(1))
                        if 0 <= apy_value <= 10:
                            return apy_value
                    except ValueError:
                        continue

        return None

    def _extract_apy_from_structured_data(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract APY from tables or other structured content."""

        # Look for tables that might contain rate information
        tables = soup.find_all("table")
        for table in tables:
            table_text = table.get_text()
            if re.search(r"apy|rate|yield|interest", table_text, re.IGNORECASE):
                # Look for percentage values in the table
                percentages = re.findall(r"(\d+\.?\d*)\s*%", table_text)
                for pct in percentages:
                    try:
                        apy_value = float(pct)
                        if 0 <= apy_value <= 10:
                            return apy_value
                    except ValueError:
                        continue

        # Look for divs or sections with rate-related classes
        rate_sections = soup.find_all(
            ["div", "section", "span"],
            class_=re.compile(r"rate|apy|yield|interest", re.IGNORECASE),
        )

        for section in rate_sections:
            text = section.get_text()
            # Look for the highest percentage that seems reasonable for a savings APY
            percentages = re.findall(r"(\d+\.?\d*)\s*%", text)
            for pct in percentages:
                try:
                    apy_value = float(pct)
                    if 2 <= apy_value <= 7:  # More restrictive range for savings APY
                        return apy_value
                except ValueError:
                    continue

        return None

    def close(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """Example usage."""
    with AllyScraper(headless=True) as scraper:
        apy = scraper.get_apy()

        print("\nScraping Results:")
        print("-" * 30)
        if apy is not None:
            print(f"Ally Bank Online Savings APY: {apy}%")
        else:
            print("Ally Bank APY: Not found")


if __name__ == "__main__":
    main()

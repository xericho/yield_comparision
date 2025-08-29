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


class YieldScraper:
    """Scraper for Vanguard mutual fund SEC yields and Ally Bank APY."""

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
            print(f"Fetching {symbol.upper()} from {url}")
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
            self.driver.quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """Example usage."""
    symbols = ["vusxx", "vctxx"]  # Add more symbols as needed

    with YieldScraper(headless=True) as scraper:
        scraper.get_multiple_yields(symbols)
        scraper.get_apy()


if __name__ == "__main__":
    main()

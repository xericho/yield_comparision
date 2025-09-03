# Yield Comparision
Yield comparison script for HYSA vs VUSXX vs VCTXX.

For current yields, see:
- [VUSXX](https://investor.vanguard.com/investment-products/mutual-funds/profile/vusxx)
- [VCTXX](https://investor.vanguard.com/investment-products/mutual-funds/profile/vctxx)
- [Ally HYSA](https://www.ally.com/bank/online-savings-account/)

## Getting Started

### Prerequisites
* Install Chromedriver 
* Install required dependencies:
  ```bash
  pip install -r requirements.txt
  ```
### Running code
Run the comparison script:
  ```bash
  python compare_yields.py --scrape
  ```

The script will fetch the latest yields from the sources listed above and update the `results.md` file.
See `python compare_yields.py -h` for more options.

## Yield Comparision Results
The latest yield calculations are available in [results.md](results.md). Results are updated daily using Github Actions.

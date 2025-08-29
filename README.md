# Yield Comparision
Yield comparison script for HYSA vs VUSXX vs VCTXX.

For current yields, see:
- [VUSXX](https://investor.vanguard.com/investment-products/mutual-funds/profile/vusxx)
- [VCTXX](https://investor.vanguard.com/investment-products/mutual-funds/profile/vctxx)
- [Ally HYSA](https://www.ally.com/bank/online-savings-account/)

## Getting Started

Install required dependencies:
  ```bash
  pip install -r requirements.txt
  ```

Run the comparison script:
  ```bash
  python compare_yields.py --scrape
  ```

The script will fetch the latest yields from the sources listed above and update the `results.md` file.

## Yield Comparision Results
The latest yield calculations are available in [results.md](results.md). Results are updated daily using Github Actions.
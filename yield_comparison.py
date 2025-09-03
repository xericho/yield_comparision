"""Yield comparison script for HYSA vs VUSXX vs VCTXX.

Assumptions:
- SEC yields passed in are already net of expense ratios (standard definition)
- HYSA interest fully taxable at federal and state level
- VUSXX: federally taxable, state tax-exempt (Treasury-only assumption)
- VCTXX: exempt from both federal and (in-state) CA tax (user context). If partial taxation applies,
  user can adjust flags/parameters accordingly.
- The marginal tax rates are used to approximate after-tax dollar yields.
"""

from __future__ import annotations

import os
import requests
from dataclasses import dataclass
from typing import List
from datetime import datetime
import argparse

from selenium_scraper import YieldScraper


# Default yields if scraping fails
DEFAULT_VUSXX_YIELD = 4.24
DEFAULT_VCTXX_YIELD = 2.36
DEFAULT_HYSA_APY = 3.5


@dataclass
class Instrument:
    name: str
    rate: float  # decimal form (e.g., 0.0424 for 4.24%)
    federal_taxable: bool
    state_taxable: bool
    state_taxable_fraction: float = (
        1.0  # Fraction of yield subject to state tax if state_taxable
    )

    def after_tax_yield(self, fed_rate: float, state_rate: float) -> float:
        """Compute the after-tax yield (decimal) for this instrument.

        Parameters
        ----------
        fed_rate : float
            Marginal federal tax rate (decimal, e.g. 0.32)
        state_rate : float
            Marginal state tax rate (decimal, e.g. 0.0738)
        """
        y = self.rate
        federal_hit = y * fed_rate if self.federal_taxable else 0.0
        state_hit = (
            y * self.state_taxable_fraction * state_rate if self.state_taxable else 0.0
        )
        return y - federal_hit - state_hit


def format_pct(x: float) -> str:
    return f"{x*100:.4f}%"


def add_common_instruments(args) -> List[Instrument]:
    return [
        Instrument(
            "VUSXX", args.vusxx / 100.0, federal_taxable=True, state_taxable=False
        ),
        Instrument(
            "VCTXX", args.vctxx / 100.0, federal_taxable=False, state_taxable=False
        ),
        Instrument("HYSA", args.hysa / 100.0, federal_taxable=True, state_taxable=True),
    ]


def compute(args) -> list[str]:
    output = []
    instruments = add_common_instruments(args)
    fed_rate = args.fed / 100.0
    state_rate = args.state / 100.0

    output = []

    output.append(f"\nPrincipal: ${args.principal:,.2f}")

    output.append("\nInput yields:")
    output.append(f"  VUSXX: {args.vusxx}%")
    output.append(f"  VCTXX: {args.vctxx}%")
    output.append(f"  HYSA: {args.hysa}%")

    output.append("\nAfter-tax yields:")

    results = []
    for inst in instruments:
        after_tax = inst.after_tax_yield(fed_rate, state_rate)
        annual_dollars = args.principal * after_tax
        results.append((inst, after_tax, annual_dollars))

    # Sort by after-tax yield descending to assign ranking
    ranked = sorted(results, key=lambda r: r[1], reverse=True)

    # Build map from instrument name to rank for quick lookup
    rank_map = {inst.name: idx + 1 for idx, (inst, _, _) in enumerate(ranked)}

    # Print consolidated lines in ranking order showing rank, name, after-tax yield, dollars
    for inst, after_tax, annual_dollars in ranked:
        r = rank_map[inst.name]
        output.append(
            f"  {r}. {inst.name}: {format_pct(after_tax)} -> ${annual_dollars:,.0f}"
        )

    # Specific pairwise differences for clarity
    def get(name: str):
        for inst, after_tax, dollars in results:
            if inst.name == name:
                return after_tax, dollars
        raise KeyError(name)

    vusxx_after_tax, vusxx_d = get("VUSXX")
    vctxx_after_tax, vctxx_d = get("VCTXX")
    hysa_after_tax, hysa_d = get("HYSA")

    output.append("\nAnnual dollar differences:")

    def diff_line(name_a: str, dollars_a: float, name_b: str, dollars_b: float) -> str:
        diff = dollars_a - dollars_b
        # Avoid division by zero; if baseline is zero, show N/A
        if dollars_b != 0:
            pct = diff / dollars_b * 100.0
            pct_str = f"{pct:+.2f}%"
        else:
            pct_str = "N/A"
        return f"  {name_a} - {name_b}: ${diff:,.0f} ({pct_str})"

    output.append(diff_line("VUSXX", vusxx_d, "HYSA", hysa_d))
    output.append(diff_line("VUSXX", vusxx_d, "VCTXX", vctxx_d))
    output.append(diff_line("VCTXX", vctxx_d, "HYSA", hysa_d))

    # Sensitivity example: partial state taxation for VUSXX (if ever applicable)
    if args.vusxx_state_taxable_fraction is not None:
        fraction = args.vusxx_state_taxable_fraction
        if fraction > 0:
            vusxx_partial = Instrument(
                "VUSXX_partial",
                args.vusxx / 100.0,
                federal_taxable=True,
                state_taxable=True,
                state_taxable_fraction=fraction,
            )
            at_partial = vusxx_partial.after_tax_yield(fed_rate, state_rate)
            output.append("\nSensitivity: VUSXX partially state-taxable")
            output.append(f"  Assumed state-taxable fraction: {fraction*100:.1f}%")
            output.append(
                f"  After-tax yield: {format_pct(at_partial)} (vs {format_pct(vusxx_after_tax)})"
            )
            output.append(
                f"  Annual dollars: ${args.principal * at_partial:,.0f} (vs ${vusxx_d:,.0f})"
            )

    # Print all collected output at the end
    print("\n".join(output))
    return output


def scrape_yields(args) -> list[str]:
    """Scrape current SEC yields from Vanguard and update args."""
    output = []
    symbols = ["vusxx", "vctxx"]
    with YieldScraper() as scraper:
        for symbol in symbols:
            sec_yield = scraper.get_sec_yield(symbol)
            if sec_yield is not None:
                args.__setattr__(symbol, sec_yield)
                output.append(
                    f"✅ Scraped SEC yield for {symbol.upper()}: {sec_yield}%"
                )
            else:
                output.append(f"❌ Failed to scrape SEC yield for {symbol.upper()}")
        apy = scraper.get_apy()
        if apy is not None:
            args.hysa = apy
            output.append(f"✅ Scraped APY for Ally: {apy}%")
        else:
            output.append(f"❌ Failed to scrape APY for Ally")

    print("\n".join(output))
    return output


def parse_args():
    p = argparse.ArgumentParser(
        description="Compare after-tax yields: VUSXX vs VCTXX vs HYSA"
    )
    p.add_argument(
        "--principal",
        type=float,
        default=100_000,
        help="Principal amount (default 100000)",
    )
    p.add_argument(
        "--vusxx",
        type=float,
        default=DEFAULT_VUSXX_YIELD,
        help=f"VUSXX SEC yield percent (default {DEFAULT_VUSXX_YIELD})",
    )
    p.add_argument(
        "--vctxx",
        type=float,
        default=DEFAULT_VCTXX_YIELD,
        help=f"VCTXX SEC yield percent (default {DEFAULT_VCTXX_YIELD})",
    )
    p.add_argument(
        "--hysa",
        type=float,
        default=DEFAULT_HYSA_APY,
        help=f"HYSA APY percent (default {DEFAULT_HYSA_APY})",
    )
    p.add_argument(
        "--fed",
        type=float,
        default=32.0,
        help="Federal marginal tax rate percent (default 32.0)",
    )
    p.add_argument(
        "--state",
        type=float,
        default=9.3,
        help="State marginal tax rate percent (default 9.3)",
    )
    p.add_argument(
        "--vusxx-state-taxable-fraction",
        type=float,
        default=0.0,
        help="If >0, treat that fraction of VUSXX yield as state-taxable for sensitivity (e.g. 0.05)",
    )
    p.add_argument(
        "--scrape",
        "-s",
        action="store_true",
        help="Whether to scrape current yields",
    )
    p.add_argument(
        "--add_results",
        action="store_true",
        help="Add results to results.md",
    )
    p.add_argument(
        "--ntfy",
        action="store_true",
        help="Send notification via ntfy (requires env vars NTFY_CRED and NTFY_URL)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    today = datetime.now().strftime("%Y-%m-%d")
    output1, output2 = [], []

    if args.scrape:
        output1 = scrape_yields(args)

    output2 = compute(args)

    if args.add_results:
        # Add date header and code block to output
        output = output1 + output2
        output = f"\n## {today}\n```\n" + "\n".join(output) + "\n```\n"

        # Read existing file or create new one with header
        with open("results.md", "r") as f:
            lines = f.readlines()

        # Insert output after the first line
        lines = [lines[0]] + [output] + lines[1:]

        # Write back to file
        with open("results.md", "w") as f:
            f.writelines(lines)

    if args.ntfy:
        ntfy_creds = os.getenv("NTFY_CREDS", "")  # base64 access token
        ntfy_url = os.getenv("NTFY_URL", "")
        notification_message = "\n".join(output1 + output2)
        response = requests.post(
            ntfy_url,
            headers={
                "Title": today,
                "Authorization": f"Bearer {ntfy_creds}",
            },
            data=notification_message.encode(encoding="utf-8"),
        )

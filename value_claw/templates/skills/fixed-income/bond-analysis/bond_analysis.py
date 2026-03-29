#!/usr/bin/env python3
"""Bond analysis: YTM, duration, convexity, and current yield calculator."""

from __future__ import annotations

import argparse
import json
import os

DATA_DIR = os.path.expanduser("~/.value_claw/bond-analysis")


def bond_price_from_ytm(
    face: float, coupon_rate: float, periods: int, ytm_per_period: float
) -> float:
    """Theoretical price given a yield per period."""
    coupon = face * coupon_rate / 2 if periods > 0 else 0
    pv_coupons = sum(coupon / (1 + ytm_per_period) ** t for t in range(1, periods + 1))
    pv_face = face / (1 + ytm_per_period) ** periods
    return pv_coupons + pv_face


def compute_ytm(
    face: float, coupon_rate: float, years: float, price: float, frequency: int = 2,
    tol: float = 1e-8, max_iter: int = 200,
) -> float | None:
    """Solve for YTM using Newton's method. Returns annualized YTM."""
    periods = int(years * frequency)
    coupon = face * coupon_rate / frequency
    ytm = coupon_rate  # initial guess

    for _ in range(max_iter):
        r = ytm / frequency
        if r <= -1:
            r = 0.001
        pv = sum(coupon / (1 + r) ** t for t in range(1, periods + 1))
        pv += face / (1 + r) ** periods
        diff = pv - price

        dpv = sum(-t * coupon / frequency / (1 + r) ** (t + 1) for t in range(1, periods + 1))
        dpv += -periods / frequency * face / (1 + r) ** (periods + 1)

        if abs(dpv) < 1e-14:
            break
        ytm -= diff / dpv
        if abs(diff) < tol:
            return ytm

    return ytm if abs(bond_price_from_ytm(face, coupon_rate, periods, ytm / frequency) - price) < 0.01 else None


def compute_duration_convexity(
    face: float, coupon_rate: float, years: float, ytm: float, frequency: int = 2,
) -> dict:
    """Compute Macaulay duration, modified duration, and convexity."""
    periods = int(years * frequency)
    coupon = face * coupon_rate / frequency
    r = ytm / frequency
    price = bond_price_from_ytm(face, coupon_rate, periods, r)

    mac_dur = 0.0
    convexity = 0.0
    for t in range(1, periods + 1):
        cf = coupon if t < periods else coupon + face
        pv_cf = cf / (1 + r) ** t
        mac_dur += t * pv_cf
        convexity += t * (t + 1) * pv_cf

    mac_dur = mac_dur / price / frequency
    convexity = convexity / (price * frequency**2 * (1 + r) ** 2)
    mod_dur = mac_dur / (1 + r)

    return {
        "macaulay_duration": round(mac_dur, 4),
        "modified_duration": round(mod_dur, 4),
        "convexity": round(convexity, 4),
    }


def analyze_bond(
    face: float, coupon_rate: float, years: float, price: float, frequency: int = 2,
) -> dict:
    """Full bond analysis."""
    coupon_rate_dec = coupon_rate / 100
    current_yield = (face * coupon_rate_dec) / price * 100 if price > 0 else 0
    ytm = compute_ytm(face, coupon_rate_dec, years, price, frequency)
    dur_conv = compute_duration_convexity(face, coupon_rate_dec, years, ytm, frequency) if ytm else {}

    return {
        "face_value": face,
        "coupon_rate_pct": coupon_rate,
        "years_to_maturity": years,
        "market_price": price,
        "frequency": frequency,
        "current_yield_pct": round(current_yield, 4),
        "ytm_pct": round(ytm * 100, 4) if ytm else None,
        "premium_discount": round(price - face, 2),
        **dur_conv,
    }


def format_text(result: dict) -> str:
    lines = [
        "Bond Analysis",
        "=" * 40,
        f"  Face Value:        ${result['face_value']:,.2f}",
        f"  Coupon Rate:       {result['coupon_rate_pct']:.2f}%",
        f"  Maturity:          {result['years_to_maturity']} years",
        f"  Market Price:      ${result['market_price']:,.2f}",
        f"  Frequency:         {result['frequency']}x/year",
        "",
        f"  Current Yield:     {result['current_yield_pct']:.4f}%",
        f"  YTM:               {result['ytm_pct']:.4f}%" if result.get("ytm_pct") else "  YTM:               N/A",
        f"  Premium/Discount:  ${result['premium_discount']:+,.2f}",
        "",
        f"  Macaulay Duration: {result.get('macaulay_duration', 'N/A')} years",
        f"  Modified Duration: {result.get('modified_duration', 'N/A')}",
        f"  Convexity:         {result.get('convexity', 'N/A')}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bond analysis: YTM, duration, convexity.")
    parser.add_argument("--face", type=float, default=1000, help="Face/par value")
    parser.add_argument("--coupon", type=float, required=True, help="Annual coupon rate (%%)")
    parser.add_argument("--maturity", type=float, required=True, help="Years to maturity")
    parser.add_argument("--price", type=float, required=True, help="Current market price")
    parser.add_argument("--frequency", type=int, default=2, help="Coupon frequency per year")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    result = analyze_bond(args.face, args.coupon, args.maturity, args.price, args.frequency)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(format_text(result))


if __name__ == "__main__":
    main()

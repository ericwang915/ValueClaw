#!/usr/bin/env python3
"""Daily K-line technical analysis: MA, MACD, RSI, Bollinger Bands, KDJ, ATR, OBV."""

import argparse
import json
import math
import sys

try:
    import pandas as pd
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)


# ── Indicator calculations (pure pandas) ────────────────────────────────────

def _sma(s, n):
    return s.rolling(n, min_periods=n).mean()


def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def _rsi(s, n=14):
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_g = gain.ewm(com=n - 1, adjust=False).mean()
    avg_l = loss.ewm(com=n - 1, adjust=False).mean()
    rs = avg_g / avg_l.replace(0, float("nan"))
    return 100 - 100 / (1 + rs)


def _macd(s, fast=12, slow=26, signal=9):
    macd_line = _ema(s, fast) - _ema(s, slow)
    sig_line = _ema(macd_line, signal)
    return macd_line, sig_line, macd_line - sig_line


def _bollinger(s, n=20, k=2):
    mid = _sma(s, n)
    std = s.rolling(n).std()
    return mid + k * std, mid, mid - k * std


def _kdj(high, low, close, n=9, m1=3, m2=3):
    lo_n = low.rolling(n, min_periods=n).min()
    hi_n = high.rolling(n, min_periods=n).max()
    denom = (hi_n - lo_n).replace(0, float("nan"))
    rsv = 100 * (close - lo_n) / denom
    K = rsv.ewm(com=m1 - 1, adjust=False).mean()
    D = K.ewm(com=m2 - 1, adjust=False).mean()
    return K, D, 3 * K - 2 * D


def _atr(high, low, close, n=14):
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(com=n - 1, adjust=False).mean()


def _obv(close, vol):
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (direction * vol).cumsum()


# ── Formatting helpers ───────────────────────────────────────────────────────

def _v(val, fmt=".2f"):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    return format(float(val), fmt)


def _pct(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    return f"{float(val) * 100:.1f}%"


# ── Main analysis ────────────────────────────────────────────────────────────

def analyze(symbol: str, period: str = "1y", show: str = "all") -> str:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)

    if df.empty:
        return f"Error: no price data found for '{symbol}'."

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    n = len(df)

    # Compute indicators
    for p in [5, 10, 20, 60, 120, 250]:
        if n >= p:
            df[f"MA{p}"] = _sma(close, p)

    df["EMA12"] = _ema(close, 12)
    df["EMA26"] = _ema(close, 26)
    df["MACD"], df["MACDsig"], df["MACDhist"] = _macd(close)
    df["RSI"] = _rsi(close)
    df["BBU"], df["BBM"], df["BBL"] = _bollinger(close)
    df["K"], df["D"], df["J"] = _kdj(high, low, close)
    df["ATR"] = _atr(high, low, close)
    df["OBV"] = _obv(close, volume)
    df["VolRatio"] = volume / volume.rolling(20).mean()

    cur = df.iloc[-1]
    prv = df.iloc[-2] if n > 1 else cur
    price = float(cur["Close"])
    date_str = df.index[-1].strftime("%Y-%m-%d")
    vol_ratio = cur.get("VolRatio", float("nan"))

    lines = [
        f"{'═' * 52}",
        f"  Technical Analysis: {symbol.upper()}",
        f"  Date: {date_str}   Price: {price:.2f}   "
        f"Vol: {int(cur['Volume']):,}   VolRatio: {_v(vol_ratio, '.2f')}x",
        f"{'═' * 52}",
    ]

    # ── Moving Averages ──────────────────────────────────────────────────────
    if show in ("all", "ma"):
        lines.append("\n── Moving Averages ───────────────────────────────")
        for p in [5, 10, 20, 60, 120, 250]:
            key = f"MA{p}"
            if key in cur.index and not math.isnan(float(cur[key])):
                ma_val = float(cur[key])
                arrow = "▲" if price >= ma_val else "▼"
                dist = (price / ma_val - 1) * 100
                lines.append(f"  MA{p:>3}: {ma_val:>10.2f}  {arrow} {dist:+.1f}%")

        # Golden / Death cross (MA20 vs MA60)
        m20c, m60c = cur.get("MA20", float("nan")), cur.get("MA60", float("nan"))
        m20p, m60p = prv.get("MA20", float("nan")), prv.get("MA60", float("nan"))
        try:
            if float(m20p) < float(m60p) and float(m20c) >= float(m60c):
                lines.append("  ⭐ Golden Cross  (MA20 crossed above MA60 — bullish)")
            elif float(m20p) > float(m60p) and float(m20c) <= float(m60c):
                lines.append("  ☠️  Death Cross   (MA20 crossed below MA60 — bearish)")
        except (TypeError, ValueError):
            pass

    # ── MACD ────────────────────────────────────────────────────────────────
    if show in ("all", "macd"):
        macd_v = cur.get("MACD", float("nan"))
        sig_v = cur.get("MACDsig", float("nan"))
        hist_v = cur.get("MACDhist", float("nan"))
        prev_hist = prv.get("MACDhist", float("nan"))
        lines.append("\n── MACD (12, 26, 9) ──────────────────────────────")
        lines.append(f"  MACD:     {_v(macd_v, '+.4f')}")
        lines.append(f"  Signal:   {_v(sig_v, '+.4f')}")
        lines.append(f"  Hist:     {_v(hist_v, '+.4f')}")
        try:
            hc, hp = float(hist_v), float(prev_hist)
            if hp < 0 < hc:
                lines.append("  ✅ Bullish crossover — MACD crossed above Signal")
            elif hp > 0 > hc:
                lines.append("  ⚠️  Bearish crossover — MACD crossed below Signal")
            elif hc > 0:
                lines.append("  📈 Above zero — bullish momentum")
            else:
                lines.append("  📉 Below zero — bearish momentum")
        except (TypeError, ValueError):
            pass

    # ── RSI ─────────────────────────────────────────────────────────────────
    if show in ("all", "rsi"):
        rsi_v = cur.get("RSI", float("nan"))
        lines.append("\n── RSI (14) ──────────────────────────────────────")
        try:
            rv = float(rsi_v)
            bar_len = int(rv / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            if rv >= 70:
                signal = "⚠️  Overbought — consider taking profit"
            elif rv <= 30:
                signal = "✅ Oversold — potential buy opportunity"
            elif rv >= 60:
                signal = "📈 Strong zone (60–70)"
            elif rv <= 40:
                signal = "📉 Weak zone (30–40)"
            else:
                signal = "➡️  Neutral (40–60)"
            lines.append(f"  RSI: {rv:5.1f}  [{bar}]")
            lines.append(f"         {signal}")
        except (TypeError, ValueError):
            lines.append("  RSI: N/A")

    # ── Bollinger Bands ──────────────────────────────────────────────────────
    if show in ("all", "bb"):
        bbu = cur.get("BBU", float("nan"))
        bbm = cur.get("BBM", float("nan"))
        bbl = cur.get("BBL", float("nan"))
        lines.append("\n── Bollinger Bands (20, 2σ) ───────────────────────")
        try:
            u, m, l = float(bbu), float(bbm), float(bbl)
            width = (u - l) / m * 100
            pos = (price - l) / (u - l) * 100
            lines.append(f"  Upper:    {u:>10.2f}")
            lines.append(f"  Mid:      {m:>10.2f}")
            lines.append(f"  Lower:    {l:>10.2f}")
            lines.append(f"  Width:    {width:.1f}%   Position: {pos:.0f}%")
            if price > u:
                lines.append("  ⚠️  Price above upper band — potentially overbought")
            elif price < l:
                lines.append("  ✅ Price below lower band — potentially oversold")
            elif pos > 80:
                lines.append("  📈 Near upper band — strong momentum")
            elif pos < 20:
                lines.append("  📉 Near lower band — weak momentum")
        except (TypeError, ValueError):
            lines.append("  Bollinger Bands: N/A (insufficient data)")

    # ── KDJ ─────────────────────────────────────────────────────────────────
    if show in ("all", "kdj"):
        k_v = cur.get("K", float("nan"))
        d_v = cur.get("D", float("nan"))
        j_v = cur.get("J", float("nan"))
        k_p = prv.get("K", float("nan"))
        d_p = prv.get("D", float("nan"))
        lines.append("\n── KDJ (9, 3, 3) ────────────────────────────────")
        try:
            kc, dc, jc = float(k_v), float(d_v), float(j_v)
            kp, dp = float(k_p), float(d_p)
            lines.append(f"  K: {kc:6.1f}   D: {dc:6.1f}   J: {jc:6.1f}")
            if kp <= dp and kc > dc:
                lines.append("  ✅ KDJ Golden Cross — K crossed above D (bullish)")
            elif kp >= dp and kc < dc:
                lines.append("  ⚠️  KDJ Death Cross — K crossed below D (bearish)")
            elif jc > 90:
                lines.append("  ⚠️  J > 90 — overbought signal")
            elif jc < 10:
                lines.append("  ✅ J < 10 — oversold signal")
        except (TypeError, ValueError):
            lines.append("  KDJ: N/A (insufficient data)")

    # ── ATR & Volatility ─────────────────────────────────────────────────────
    if show in ("all", "vol"):
        atr_v = cur.get("ATR", float("nan"))
        lines.append("\n── ATR & Volatility (14-period) ──────────────────")
        try:
            av = float(atr_v)
            atr_pct = av / price * 100
            lines.append(f"  ATR:  {av:.2f}  ({atr_pct:.1f}% of price)")
            if atr_pct > 5:
                lines.append("  ⚡ High volatility")
            elif atr_pct < 1:
                lines.append("  😴 Low volatility")
        except (TypeError, ValueError):
            pass

    # ── Signal Summary ───────────────────────────────────────────────────────
    lines.append("\n── Signal Summary ────────────────────────────────")
    signals = []

    # MA trend
    ma20c = cur.get("MA20", float("nan"))
    ma60c = cur.get("MA60", float("nan"))
    try:
        if price > float(ma20c) > float(ma60c):
            signals.append(("MA 趋势", "多头排列 ▲ (Bullish alignment)", "✅"))
        elif price < float(ma20c) < float(ma60c):
            signals.append(("MA 趋势", "空头排列 ▼ (Bearish alignment)", "⚠️"))
        else:
            signals.append(("MA 趋势", "混合 (Mixed)", "➡️"))
    except (TypeError, ValueError):
        pass

    # RSI
    try:
        rv = float(cur.get("RSI", float("nan")))
        if rv >= 70:
            signals.append(("RSI", f"{rv:.1f} — Overbought", "⚠️"))
        elif rv <= 30:
            signals.append(("RSI", f"{rv:.1f} — Oversold", "✅"))
        else:
            signals.append(("RSI", f"{rv:.1f} — Neutral", "➡️"))
    except (TypeError, ValueError):
        pass

    # MACD
    try:
        hc = float(cur.get("MACDhist", float("nan")))
        signals.append(("MACD", "Bullish" if hc > 0 else "Bearish", "✅" if hc > 0 else "⚠️"))
    except (TypeError, ValueError):
        pass

    # KDJ
    try:
        kc, dc = float(cur.get("K", float("nan"))), float(cur.get("D", float("nan")))
        signals.append(("KDJ", f"K{'>' if kc > dc else '<'}D ({'Bullish' if kc > dc else 'Bearish'})", "✅" if kc > dc else "⚠️"))
    except (TypeError, ValueError):
        pass

    for label, val, icon in signals:
        lines.append(f"  {icon} {label:<10} {val}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Daily K-line technical analysis.")
    parser.add_argument("symbol", help="Ticker symbol (e.g. AAPL, 600519.SS, BTC-USD)")
    parser.add_argument("--period", default="1y",
                        help="Lookback period: 3mo, 6mo, 1y (default), 2y, 5y")
    parser.add_argument("--show", default="all",
                        choices=["all", "ma", "macd", "rsi", "bb", "kdj", "vol"],
                        help="Which indicators to show")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.format == "json":
        ticker = yf.Ticker(args.symbol)
        df = ticker.history(period=args.period)
        if df.empty:
            print(json.dumps({"error": f"No data for {args.symbol}"}))
            return
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        df["RSI"] = _rsi(close)
        df["MACD"], df["MACDsig"], df["MACDhist"] = _macd(close)
        df["BBU"], df["BBM"], df["BBL"] = _bollinger(close)
        df["K"], df["D"], df["J"] = _kdj(high, low, close)
        df["ATR"] = _atr(high, low, close)
        for p in [5, 10, 20, 60]:
            df[f"MA{p}"] = _sma(close, p)
        last = df.tail(5)
        records = []
        for idx, row in last.iterrows():
            rec = {"date": idx.strftime("%Y-%m-%d")}
            for col in ["Close", "Volume", "RSI", "MACD", "MACDhist", "K", "D", "J",
                        "BBU", "BBM", "BBL", "ATR", "MA5", "MA10", "MA20", "MA60"]:
                if col in row:
                    v = row[col]
                    rec[col] = round(float(v), 4) if not math.isnan(float(v)) else None
            records.append(rec)
        print(json.dumps({"symbol": args.symbol.upper(), "indicators": records}, indent=2))
        return

    result = analyze(args.symbol, period=args.period, show=args.show)
    print(result)


if __name__ == "__main__":
    main()

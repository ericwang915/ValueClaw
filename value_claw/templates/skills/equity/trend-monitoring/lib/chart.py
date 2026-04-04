#!/usr/bin/env python3
"""Stock analysis and candlestick chart generation with technical indicators."""

import datetime
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.signal import argrelextrema


def calculate_rsi(data, window=14):
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_macd(data, slow=26, fast=12, signal=9):
    exp1 = data["Close"].ewm(span=fast, adjust=False).mean()
    exp2 = data["Close"].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line


def calculate_bollinger_bands(data, window=20, num_std=2):
    rolling_mean = data["Close"].rolling(window=window).mean()
    rolling_std = data["Close"].rolling(window=window).std()
    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)
    return upper_band, lower_band


def get_reversal_signals(data):
    signals = []
    for i in range(len(data)):
        if i < 26:
            signals.append(None)
            continue

        current = data.iloc[i]
        prev = data.iloc[i - 1]
        signal = None

        macd_cross_up = (prev["MACD"] < prev["Signal_Line"]) and (
            current["MACD"] > current["Signal_Line"]
        )
        macd_cross_dn = (prev["MACD"] > prev["Signal_Line"]) and (
            current["MACD"] < current["Signal_Line"]
        )
        rsi_oversold = current["RSI"] < 30
        rsi_overbought = current["RSI"] > 70
        bb_rev_buy = (prev["Low"] <= prev["Lower_BB"]) and (
            current["Close"] > current["Lower_BB"]
        )
        bb_rev_sell = (prev["High"] >= prev["Upper_BB"]) and (
            current["Close"] < current["Upper_BB"]
        )

        if (rsi_oversold and macd_cross_up) or bb_rev_buy:
            signal = "Buy"
        if (rsi_overbought and macd_cross_dn) or bb_rev_sell:
            signal = "Sell"

        signals.append(signal)
    return signals


def find_patterns(data, order=5):
    """Detect Double Bottom/Top, Head & Shoulders patterns via local extrema."""
    prices = data["Close"].values
    max_idx = argrelextrema(prices, np.greater, order=order)[0]
    min_idx = argrelextrema(prices, np.less, order=order)[0]
    patterns = []

    for i in range(len(min_idx) - 1):
        idx1, idx2 = min_idx[i], min_idx[i + 1]
        p1, p2 = prices[idx1], prices[idx2]
        if abs(1 - (p1 / p2)) < 0.03:
            peaks = [p for p in max_idx if idx1 < p < idx2]
            if peaks and prices[peaks[0]] > max(p1, p2) * 1.02:
                patterns.append({"type": "Double Bottom", "color": "lime"})

    for i in range(len(max_idx) - 1):
        idx1, idx2 = max_idx[i], max_idx[i + 1]
        p1, p2 = prices[idx1], prices[idx2]
        if abs(1 - (p1 / p2)) < 0.03:
            troughs = [t for t in min_idx if idx1 < t < idx2]
            if troughs and prices[troughs[0]] < min(p1, p2) * 0.98:
                patterns.append({"type": "Double Top", "color": "red"})

    if len(max_idx) >= 3:
        for i in range(len(max_idx) - 2):
            s1, h, s2 = max_idx[i], max_idx[i + 1], max_idx[i + 2]
            ps1, ph, ps2 = prices[s1], prices[h], prices[s2]
            if ph > ps1 and ph > ps2 and abs(1 - (ps1 / ps2)) < 0.1:
                if ph > max(ps1, ps2) * 1.02:
                    patterns.append({"type": "Head & Shoulders Top", "color": "darkred"})

    if len(min_idx) >= 3:
        for i in range(len(min_idx) - 2):
            s1, h, s2 = min_idx[i], min_idx[i + 1], min_idx[i + 2]
            ps1, ph, ps2 = prices[s1], prices[h], prices[s2]
            if ph < ps1 and ph < ps2 and abs(1 - (ps1 / ps2)) < 0.1:
                if ph < min(ps1, ps2) * 0.98:
                    patterns.append({"type": "Inv Head & Shoulders", "color": "lightgreen"})

    return patterns


def analyze_recent_trend(data):
    recent = data.iloc[-30:].copy()
    if len(recent) < 5:
        return 0, 0, "Insuff. Data"

    x = np.arange(len(recent))
    y = recent["Close"].values
    slope, intercept = np.polyfit(x, y, 1)
    start_reg = slope * x[0] + intercept
    end_reg = slope * x[-1] + intercept
    pct_change = (end_reg - start_reg) / start_reg

    if pct_change > 0.05:
        status = "Strong Uptrend"
    elif pct_change > 0.01:
        status = "Uptrend"
    elif pct_change < -0.05:
        status = "Strong Downtrend"
    elif pct_change < -0.01:
        status = "Downtrend"
    else:
        status = "Ranging"

    return slope, pct_change, status


def generate_stock_chart(ticker, data, output_dir):
    """Generate a professional candlestick chart with indicator panels. Returns path to saved PNG."""
    end_date = data.index[-1]
    start_date = end_date - datetime.timedelta(days=180)
    plot_data = data.loc[start_date:]
    if plot_data.empty:
        return None

    mc = mpf.make_marketcolors(up="#26a69a", down="#ef5350", inherit=True)
    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mc,
        gridcolor="#2a2e39",
        gridstyle=":",
        facecolor="#0b0f19",
        figcolor="#0b0f19",
        rc={
            "axes.edgecolor": "#2a2e39",
            "xtick.color": "white",
            "ytick.color": "white",
            "text.color": "white",
            "font.size": 10,
            "axes.labelcolor": "white",
        },
    )

    apds = [
        mpf.make_addplot(plot_data["Upper_BB"], color="#00ffff", linestyle="--", width=0.8),
        mpf.make_addplot(plot_data["Lower_BB"], color="#ff00ff", linestyle="--", width=0.8),
        mpf.make_addplot(plot_data["SMA_20"], color="#ffd700", width=1),
        mpf.make_addplot(plot_data["SMA_50"], color="#9370db", width=1.2),
        mpf.make_addplot(plot_data["RSI"], panel=2, color="#da70d6", width=1.2, ylabel="RSI"),
        mpf.make_addplot(plot_data["MACD"], panel=3, color="#00bfff", width=1.2, ylabel="MACD"),
        mpf.make_addplot(plot_data["Signal_Line"], panel=3, color="#ff8c00", width=1.2),
    ]

    buy_signals, sell_signals = [], []
    for i in range(len(plot_data)):
        sig = plot_data["Signal"].iloc[i]
        if sig == "Buy":
            buy_signals.append(plot_data["Low"].iloc[i] * 0.98)
            sell_signals.append(np.nan)
        elif sig == "Sell":
            buy_signals.append(np.nan)
            sell_signals.append(plot_data["High"].iloc[i] * 1.02)
        else:
            buy_signals.append(np.nan)
            sell_signals.append(np.nan)

    if any(not np.isnan(x) for x in buy_signals):
        apds.append(mpf.make_addplot(buy_signals, type="scatter", markersize=100, marker="^", color="#00e676"))
    if any(not np.isnan(x) for x in sell_signals):
        apds.append(mpf.make_addplot(sell_signals, type="scatter", markersize=100, marker="v", color="#ff1744"))

    fig, axes = mpf.plot(
        plot_data,
        type="candle",
        style=style,
        addplot=apds,
        volume=True,
        panel_ratios=(10, 2, 2, 2),
        returnfig=True,
        tight_layout=True,
        figscale=1.5,
        scale_padding={"top": 5, "left": 1, "right": 1.5},
        ylabel="",
        datetime_format="%b %d",
    )

    ax_main, ax_vol, ax_rsi, ax_macd = axes[0], axes[2], axes[4], axes[6]
    fig.subplots_adjust(hspace=0.3)

    for ax in (ax_main, ax_vol, ax_rsi, ax_macd):
        ax.yaxis.tick_right()

    ax_main.set_ylabel("Price", rotation=270, labelpad=20)
    ax_main.yaxis.set_label_position("right")
    for ax, lbl in [(ax_vol, "Vol"), (ax_rsi, "RSI"), (ax_macd, "MACD")]:
        ax.set_ylabel(lbl, rotation=0, ha="right", va="center", labelpad=10)
        ax.yaxis.set_label_position("left")

    ax_main.set_title("")
    today_str = datetime.datetime.now().strftime("%b %d")
    ax_main.text(
        0.0, 1.06, f" {today_str} ",
        transform=ax_main.transAxes, color="white", fontsize=14, fontweight="bold",
        va="bottom", ha="left",
        bbox=dict(boxstyle="round,pad=0.3", fc="#e53935", ec="none"),
    )
    ax_main.text(
        0.15, 1.06, f"{ticker} Trend Analysis",
        transform=ax_main.transAxes, color="white", fontsize=14, fontweight="bold",
        va="bottom", ha="left",
    )

    trend_dir = os.path.join(output_dir, "images", "trend")
    os.makedirs(trend_dir, exist_ok=True)
    filename = os.path.join(trend_dir, f"{ticker.upper()}_trend_analysis.png")
    fig.savefig(filename, facecolor="#0b0f19", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Chart saved: {filename}")
    return filename


def analyze_stock(ticker, output_dir):
    """Full stock analysis pipeline: fetch data, compute indicators, detect patterns, generate chart."""
    end_date = datetime.datetime.now()
    fetch_date = end_date - datetime.timedelta(days=280)

    print(f"  Fetching data for {ticker}...")
    data = yf.download(ticker, start=fetch_date, end=end_date, progress=False)
    if data.empty:
        print(f"  No data found for {ticker}")
        return None

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    data["RSI"] = calculate_rsi(data)
    data["MACD"], data["Signal_Line"] = calculate_macd(data)
    data["Upper_BB"], data["Lower_BB"] = calculate_bollinger_bands(data)
    data["SMA_20"] = data["Close"].rolling(window=20).mean()
    data["SMA_50"] = data["Close"].rolling(window=50).mean()
    data["Signal"] = get_reversal_signals(data)

    patterns = find_patterns(data)
    chart_path = generate_stock_chart(ticker, data, output_dir)
    _, pct_change, trend_status = analyze_recent_trend(data)

    last = data.iloc[-1]
    prev = data.iloc[-2]
    signals = []
    if last["RSI"] < 30:
        signals.append("RSI Oversold")
    elif last["RSI"] > 70:
        signals.append("RSI Overbought")
    if (prev["MACD"] < prev["Signal_Line"]) and (last["MACD"] > last["Signal_Line"]):
        signals.append("MACD Buy")
    elif (prev["MACD"] > prev["Signal_Line"]) and (last["MACD"] < last["Signal_Line"]):
        signals.append("MACD Sell")

    return {
        "Ticker": ticker,
        "Price": float(last["Close"]),
        "RSI": float(last["RSI"]),
        "MACD_Signal": "Buy" if last["MACD"] > last["Signal_Line"] else "Sell",
        "Trend_30d": trend_status,
        "Change_30d%": float(pct_change * 100),
        "Patterns": ", ".join(p["type"] for p in patterns) if patterns else "None",
        "Signals": ", ".join(signals) if signals else "Neutral",
        "ChartPath": chart_path,
    }

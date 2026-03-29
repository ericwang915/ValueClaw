#!/usr/bin/env python3
"""TradingView technical indicator table generation as an image."""

import datetime
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from tradingview_ta import Interval, TA_Handler
except ImportError:
    TA_Handler = None


def _get_action(rec_val):
    if rec_val == 1:
        return "POSITIVE"
    if rec_val == -1:
        return "NEGATIVE"
    return "NEUTRAL"


def get_technical_analysis(ticker):
    """Fetch TradingView oscillator + MA summary for a US-listed ticker."""
    if TA_Handler is None:
        print("  tradingview-ta not installed, skipping indicator table")
        return None

    exchanges = ["NASDAQ", "NYSE", "AMEX"]
    analysis = None
    for exchange in exchanges:
        try:
            handler = TA_Handler(
                symbol=ticker,
                exchange=exchange,
                screener="america",
                interval=Interval.INTERVAL_1_DAY,
            )
            analysis = handler.get_analysis()
            if analysis:
                break
        except Exception:
            continue

    if not analysis:
        print(f"  Could not find TradingView data for {ticker}")
        return None

    try:
        d = analysis.indicators

        rsi = d.get("RSI", 0) or 0
        rsi_act = "NEGATIVE" if rsi > 70 else ("POSITIVE" if rsi < 30 else "NEUTRAL")

        stoch_k = d.get("Stoch.K", 0) or 0
        stoch_act = "NEGATIVE" if stoch_k > 80 else ("POSITIVE" if stoch_k < 20 else "NEUTRAL")

        cci = d.get("CCI20", 0) or 0
        cci_act = "NEGATIVE" if cci > 100 else ("POSITIVE" if cci < -100 else "NEUTRAL")

        adx = d.get("ADX", 0) or 0
        ao = d.get("AO", 0) or 0
        mom = d.get("Mom", 0) or 0
        macd_v = d.get("MACD.macd", 0) or 0
        macd_s = d.get("MACD.signal", 0) or 0

        oscillators = [
            {"Name": "RSI (14)", "Value": f"{rsi:.2f}", "Action": rsi_act},
            {"Name": "Stochastic %K (14,3,3)", "Value": f"{stoch_k:.2f}", "Action": stoch_act},
            {"Name": "CCI (20)", "Value": f"{cci:.2f}", "Action": cci_act},
            {"Name": "ADX (14)", "Value": f"{adx:.2f}", "Action": "NEUTRAL"},
            {"Name": "Awesome Oscillator", "Value": f"{ao:.2f}", "Action": "POSITIVE" if ao > 0 else "NEGATIVE"},
            {"Name": "Momentum (10)", "Value": f"{mom:.2f}", "Action": "POSITIVE" if mom > 0 else "NEGATIVE"},
            {"Name": "MACD (12,26)", "Value": f"{macd_v:.2f}", "Action": "POSITIVE" if macd_v > macd_s else "NEGATIVE"},
            {"Name": "Stochastic RSI", "Value": f"{d.get('Stoch.RSI.K', 0) or 0:.2f}", "Action": _get_action(d.get("Rec.Stoch.RSI", 0) or 0)},
            {"Name": "Williams %R (14)", "Value": f"{d.get('W.R', 0) or 0:.2f}", "Action": _get_action(d.get("Rec.WR", 0) or 0)},
            {"Name": "Bull Bear Power", "Value": f"{d.get('BBPower', 0) or 0:.2f}", "Action": _get_action(d.get("Rec.BBPower", 0) or 0)},
            {"Name": "Ultimate Oscillator", "Value": f"{d.get('UO', 0) or 0:.2f}", "Action": _get_action(d.get("Rec.UO", 0) or 0)},
        ]

        close = d.get("close", 0) or 0
        mas = []
        for p in [10, 20, 30, 50, 100, 200]:
            ema = d.get(f"EMA{p}", 0) or 0
            sma = d.get(f"SMA{p}", 0) or 0
            mas.append({"Name": f"EMA ({p})", "Value": f"{ema:.2f}", "Action": "POSITIVE" if close > ema else "NEGATIVE"})
            mas.append({"Name": f"SMA ({p})", "Value": f"{sma:.2f}", "Action": "POSITIVE" if close > sma else "NEGATIVE"})

        ichi = d.get("Ichimoku.BLine", 0) or 0
        mas.append({"Name": "Ichimoku Base (9,26,52)", "Value": f"{ichi:.2f}", "Action": _get_action(d.get("Rec.Ichimoku", 0) or 0)})
        vwma = d.get("VWMA", 0) or 0
        mas.append({"Name": "VWMA (20)", "Value": f"{vwma:.2f}", "Action": _get_action(d.get("Rec.VWMA", 0) or 0)})
        hma = d.get("HullMA9", 0) or 0
        mas.append({"Name": "Hull MA (9)", "Value": f"{hma:.2f}", "Action": _get_action(d.get("Rec.HullMA9", 0) or 0)})

        return {
            "Ticker": ticker,
            "Summary": analysis.summary.get("RECOMMENDATION", "UNKNOWN"),
            "Oscillators": oscillators,
            "Moving_Averages": mas,
        }
    except Exception as e:
        print(f"  Error parsing TradingView data for {ticker}: {e}")
        return None


def generate_indicator_chart(ticker, output_dir):
    """Generate indicator analysis table as a styled PNG image. Returns absolute path."""
    res = get_technical_analysis(ticker)
    if not res:
        return None

    summary = res["Summary"]
    header_color = "#2c3e50"
    section_color = "#95a5a6"
    row_even = "#f8f9fa"
    row_odd = "#e9ecef"

    rows = [["Indicator", "Value", "Action"]]
    colors = [header_color]

    rows.append([f"{ticker} Analysis (Summary: {summary})", "", ""])
    colors.append("#34495e")

    rows.append(["Oscillators", "", ""])
    colors.append(section_color)
    for i, item in enumerate(res["Oscillators"]):
        rows.append([item["Name"], item["Value"], item["Action"]])
        colors.append(row_even if i % 2 == 0 else row_odd)

    rows.append(["Moving Averages", "", ""])
    colors.append(section_color)
    for i, item in enumerate(res["Moving_Averages"]):
        rows.append([item["Name"], item["Value"], item["Action"]])
        colors.append(row_even if i % 2 == 0 else row_odd)

    num_rows = len(rows)
    row_h = 0.35
    pad = 1.0
    total_h = pad + num_rows * row_h

    fig, ax = plt.subplots(figsize=(12, total_h))
    ax.axis("off")

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title_y = 1.0 - (0.5 * pad / total_h)
    plt.title(f"{ticker} Technical Analysis ({now_str})", fontsize=16, weight="bold", color="#34495e", y=title_y, va="center")

    table = ax.table(
        cellText=rows, colLabels=None, cellLoc="center", loc="bottom",
        bbox=[0, 0, 1, (num_rows * row_h) / total_h],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)

    for (row, col), cell in table.get_celld().items():
        cell.set_height(row_h / total_h)
        rc = colors[row]
        cell.set_facecolor(rc)

        txt = cell.get_text().get_text()
        if row == 0:
            cell.set_text_props(color="white", weight="bold")
        elif rc == "#34495e":
            cell.set_text_props(color="white", weight="bold" if col == 0 else "normal", ha="left" if col == 0 else "center")
        elif rc == section_color:
            cell.set_text_props(weight="bold", color="white", ha="left" if col == 0 else "center")
        else:
            cell.set_text_props(color="black")
            if col == 2:
                if "POSITIVE" in txt:
                    cell.set_text_props(color="#008000", weight="bold")
                elif "NEGATIVE" in txt:
                    cell.set_text_props(color="#FF0000", weight="bold")
                elif "NEUTRAL" in txt:
                    cell.set_text_props(color="#7f8c8d")
            if col == 0:
                cell.set_text_props(ha="left", color="black")

    ind_dir = os.path.join(output_dir, "images", "indicators")
    os.makedirs(ind_dir, exist_ok=True)
    filename = os.path.join(ind_dir, f"{ticker.upper()}_indicator.png")
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Indicator chart saved: {filename}")
    return os.path.abspath(filename)

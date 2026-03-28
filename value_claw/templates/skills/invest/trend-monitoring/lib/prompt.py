#!/usr/bin/env python3
"""Build LLM analysis prompt from key stats and news data."""

import os
import pandas as pd
import yfinance as yf


def _format_list(lst, precision=3):
    return [round(float(x), precision) for x in lst]


def generate_key_stats(ticker, output_dir):
    """Generate key technical statistics text file for a ticker."""
    stats_dir = os.path.join(output_dir, "stats")
    os.makedirs(stats_dir, exist_ok=True)
    output_file = os.path.join(stats_dir, f"{ticker.upper()}_stats.txt")

    try:
        daily = yf.download(ticker, period="1y", interval="1d", progress=False)
        weekly = yf.download(ticker, period="2y", interval="1wk", progress=False)
        if daily.empty or weekly.empty:
            return

        for df in (daily, weekly):
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

        daily["EMA_20"] = daily["Close"].ewm(span=20, adjust=False).mean()
        macd = daily["Close"].ewm(span=12, adjust=False).mean() - daily["Close"].ewm(span=26, adjust=False).mean()
        daily["MACD"] = macd
        daily["Signal"] = macd.ewm(span=9, adjust=False).mean()

        delta = daily["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        daily["RSI"] = 100 - (100 / (1 + gain / loss))

        rm = daily["Close"].rolling(20).mean()
        rs = daily["Close"].rolling(20).std()
        daily["Upper_BB"] = rm + 2 * rs
        daily["Mid_BB"] = rm
        daily["Lower_BB"] = rm - 2 * rs

        last = daily.iloc[-1]
        price = last["Close"]
        vol_avg = daily["Volume"].rolling(20).mean().iloc[-1]
        vol_ratio = daily["Volume"].iloc[-1] / vol_avg if vol_avg > 0 else 0

        rsi_status = "Neutral"
        if last["RSI"] > 70:
            rsi_status = "Overbought (>70)"
        elif last["RSI"] < 30:
            rsi_status = "Oversold (<30)"

        bb_status = "Between bands"
        if price >= last["Upper_BB"]:
            bb_status = "Above Upper Band (Overbought)"
        elif price <= last["Lower_BB"]:
            bb_status = "Below Lower Band (Oversold)"

        pivot = (last["High"] + last["Low"] + last["Close"]) / 3
        r1 = (2 * pivot) - last["Low"]
        s1 = (2 * pivot) - last["High"]

        frac_high = daily.tail(7)["High"].max()
        frac_low = daily.tail(7)["Low"].min()

        last10 = daily.tail(10)

        weekly["EMA_20"] = weekly["Close"].ewm(span=20, adjust=False).mean()
        weekly["EMA_50"] = weekly["Close"].ewm(span=50, adjust=False).mean()

        lines = [
            f"current_price (Daily) = {price:.2f}, current_ema20 = {last['EMA_20']:.3f}, current_macd = {last['MACD']:.3f}, current_rsi = {last['RSI']:.2f}",
            "",
            "Technical Signals (Daily):",
            f"Volume Ratio (Today/Avg20): {vol_ratio:.2f} ({'High' if vol_ratio > 1 else 'Normal'})",
            f"RSI Status: {rsi_status}",
            f"Bollinger Band Status: {bb_status}",
            f"Pivot Points: P={pivot:.2f}, R1={r1:.2f}, S1={s1:.2f}",
            f"Fractal High/Low (7d): High={frac_high:.2f}, Low={frac_low:.2f}",
            "",
            "Daily series (last 10, oldest -> latest):",
            f"Close: {_format_list(last10['Close'].tolist())}",
            f"EMA20: {_format_list(last10['EMA_20'].tolist())}",
            f"MACD: {_format_list(last10['MACD'].tolist())}",
            f"RSI: {_format_list(last10['RSI'].tolist())}",
            "",
            "Weekly context:",
            f"EMA20w: {weekly['EMA_20'].iloc[-1]:.3f}, EMA50w: {weekly['EMA_50'].iloc[-1]:.3f}",
        ]

        with open(output_file, "w") as f:
            f.write("\n".join(lines))
        print(f"  Stats saved: {output_file}")
    except Exception as e:
        print(f"  Error generating stats for {ticker}: {e}")


def generate_analysis_prompt(ticker, output_dir):
    """Build the LLM analysis prompt from stats + news. Returns prompt text."""
    prompt_dir = os.path.join(output_dir, "prompt")
    os.makedirs(prompt_dir, exist_ok=True)

    stats_file = os.path.join(output_dir, "stats", f"{ticker.upper()}_stats.txt")
    news_file = os.path.join(output_dir, "news", f"{ticker.upper()}_news.csv")

    stats_content = "No statistics available."
    if os.path.exists(stats_file):
        with open(stats_file) as f:
            stats_content = f.read()

    news_content = "No recent news available."
    if os.path.exists(news_file):
        try:
            df = pd.read_csv(news_file)
            if not df.empty:
                items = []
                for _, row in df.head(5).iterrows():
                    t = row.get("time", "Unknown")
                    title = row.get("title", "No Title")
                    summary = row.get("summary", "No Summary")
                    items.append(f"- [{t}] {title}\n  Summary: {summary}")
                news_content = "\n".join(items)
        except Exception:
            pass

    market_items = []
    for idx in ["GSPC", "DJI", "IXIC"]:
        mf = os.path.join(output_dir, "news", f"{idx}_news.csv")
        if os.path.exists(mf):
            try:
                df = pd.read_csv(mf)
                for _, row in df.head(2).iterrows():
                    t = row.get("time", "Unknown")
                    title = row.get("title", "No Title")
                    summary = str(row.get("summary", ""))[:300]
                    market_items.append(f"- [{idx} | {t}] {title}\n  Summary: {summary}")
            except Exception:
                pass
    market_news = "\n".join(market_items) if market_items else "No market news available."

    prompt = f"""Role: You are a Senior Hedge Fund Manager with 20+ years of experience. Provide clear, actionable trading recommendations.

Task: Analyze technicals and news for {ticker.upper()}.

### 1. Key Technical Statistics
{stats_content}

### 2. Recent News & Sentiment ({ticker.upper()})
{news_content}

### 3. Broad Market Context (Indices)
{market_news}

### Analysis Guidelines
1. Be Decisive — identify the most relevant timeframe or catalyst NOW.
2. Neutral only if: tight consolidation, perfectly balanced indicators, or imminent catalyst (48h).
3. Provide specific price levels for entry/exit, stop loss hints.
4. Confidence: Strong Positive/Negative >75%, Positive/Negative 60-75%, Neutral <60%.

**Output Format:**
[SIGNAL]
(Strong Positive | Positive | Neutral | Negative | Strong Negative)

[CONFIDENCE]
(0-100%)

[SUMMARY]
(3-5 bullet points with KEY PRICE LEVELS)

[REASONING]
(Technical Setup, Sentiment & Catalysts, Risk/Reward, Action Plan)
"""

    out = os.path.join(prompt_dir, f"{ticker.upper()}_prompt.txt")
    with open(out, "w") as f:
        f.write(prompt)
    return prompt

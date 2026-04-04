#!/usr/bin/env python3
"""News fetching via Yahoo Finance with article summary scraping."""

import datetime
import os

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _scrape_summary(url, timeout=5):
    if not url or url == "#":
        return "No Link"
    try:
        resp = requests.get(url, headers={"User-Agent": _UA}, timeout=timeout)
        if resp.status_code != 200:
            return f"Error: HTTP {resp.status_code}"
        soup = BeautifulSoup(resp.text, "html.parser")
        paras = []
        for p in soup.find_all("p"):
            text = p.get_text().strip()
            if len(text) > 60:
                paras.append(text)
                if len(paras) >= 2:
                    break
        return "\n\n".join(paras) if paras else "Could not extract summary."
    except Exception as e:
        return f"Scraping Error: {str(e)[:50]}"


def get_recent_news(ticker, limit=5):
    """Fetch recent news items for a ticker from Yahoo Finance."""
    try:
        t = yf.Ticker(ticker)
        news_list = t.news or []
        items = []
        for item in news_list[:limit]:
            if not isinstance(item, dict):
                continue
            content = item.get("content") or {}
            title = content.get("title", "No Title")
            provider = content.get("provider") or {}
            publisher = provider.get("displayName", "Unknown")
            click = content.get("clickThroughUrl") or {}
            link = click.get("url", "#")

            pub_date = content.get("pubDate")
            time_str = "Unknown"
            if pub_date:
                try:
                    dt = datetime.datetime.strptime(pub_date, "%Y-%m-%dT%H:%M:%SZ")
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    time_str = pub_date

            summary = _scrape_summary(link)
            items.append({
                "title": title,
                "publisher": publisher,
                "link": link,
                "time": time_str,
                "summary": summary,
            })
        return items
    except Exception as e:
        print(f"  Error fetching news for {ticker}: {e}")
        return []


def fetch_all_news(tickers, output_dir):
    """Fetch and save news CSVs for tickers + market indices."""
    news_dir = os.path.join(output_dir, "news")
    os.makedirs(news_dir, exist_ok=True)

    for ticker in tickers:
        print(f"  Fetching news for {ticker}...")
        items = get_recent_news(ticker, limit=5)
        if items:
            for it in items:
                it["ticker"] = ticker
            df = pd.DataFrame(items)
            cols = ["ticker", "time", "title", "publisher", "summary", "link"]
            df = df[[c for c in cols if c in df.columns]]
            path = os.path.join(news_dir, f"{ticker.upper()}_news.csv")
            df.to_csv(path, index=False)

    for idx in ["^GSPC", "^DJI", "^IXIC"]:
        print(f"  Fetching market news for {idx}...")
        items = get_recent_news(idx, limit=5)
        if items:
            for it in items:
                it["ticker"] = idx
            df = pd.DataFrame(items)
            cols = ["ticker", "time", "title", "publisher", "summary", "link"]
            df = df[[c for c in cols if c in df.columns]]
            safe = idx.replace("^", "")
            path = os.path.join(news_dir, f"{safe}_news.csv")
            df.to_csv(path, index=False)

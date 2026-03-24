#!/usr/bin/env python3
"""Scrape and extract content from a web page."""

import argparse
import json
import sys

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print(
        "Error: requests and/or beautifulsoup4 not installed.\n"
        "Run: pip install requests beautifulsoup4",
        file=sys.stderr,
    )
    sys.exit(1)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def scrape(url: str) -> dict:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    text = soup.get_text(separator="\n", strip=True)

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        label = a.get_text(strip=True)
        if href.startswith("http"):
            links.append({"text": label, "url": href})

    headings = []
    for level in range(1, 7):
        for h in soup.find_all(f"h{level}"):
            headings.append({"level": level, "text": h.get_text(strip=True)})

    return {
        "url": url,
        "title": title,
        "text": text[:10000],
        "links": links[:100],
        "headings": headings,
    }


def main():
    parser = argparse.ArgumentParser(description="Scrape a web page.")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument(
        "--format",
        choices=["text", "json", "links", "headings"],
        default="text",
        help="Output format",
    )
    args = parser.parse_args()

    try:
        data = scrape(args.url)
    except Exception as exc:
        print(f"Error scraping {args.url}: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif args.format == "links":
        for link in data["links"]:
            print(f"  {link['text']} -> {link['url']}")
    elif args.format == "headings":
        for h in data["headings"]:
            indent = "  " * (h["level"] - 1)
            print(f"{indent}h{h['level']}: {h['text']}")
    else:
        print(f"Title: {data['title']}\n")
        print(data["text"][:5000])


if __name__ == "__main__":
    main()

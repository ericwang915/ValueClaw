import os
import sys
import urllib.parse
from typing import Any, Dict

try:
    import requests
except ImportError:
    print("Error: 'requests' module not found. Please install it via 'pip install requests'.", file=sys.stderr)
    sys.exit(1)

def get_api_key() -> str:
    # 1. Try env var
    key = os.environ.get("BRAVE_API_KEY")
    if key:
        return key

    # 2. Try value_claw.json config
    try:
        from value_claw import config
        key = config.get_str("skills", "brave", "apiKey")
        if key:
            return key
    except Exception:
        pass

    print("Error: Brave API key not found. Set BRAVE_API_KEY env var or add it to value_claw.json.", file=sys.stderr)
    sys.exit(1)

def search_brave(query: str, api_key: str) -> Dict[str, Any]:
    url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(query)}&count=10"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def main():
    if len(sys.argv) < 2:
        print("Usage: python brave.py <query>")
        sys.exit(1)

    query = sys.argv[1]
    api_key = get_api_key()

    try:
        results = search_brave(query, api_key)
        web_results = results.get("web", {}).get("results", [])

        if not web_results:
            print("No results found.")
            return

        print(f"--- Brave Search Results for: '{query}' ---")
        for i, res in enumerate(web_results, 1):
            title = res.get("title", "No Title")
            url = res.get("url", "#")
            desc = res.get("description", "No description available.")
            print(f"{i}. {title}")
            print(f"   URL: {url}")
            print(f"   {desc}\n")

    except Exception as e:
        print(f"Error executing Brave Search: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

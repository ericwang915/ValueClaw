import json
import os
import sys
from typing import Dict, Any

try:
    import requests
except ImportError:
    print("Error: 'requests' module not found. Please install it via 'pip install requests'.", file=sys.stderr)
    sys.exit(1)

def get_api_key() -> str:
    # 1. Try env var
    key = os.environ.get("PERPLEXITY_API_KEY")
    if key:
        return key
        
    # 2. Try value_claw.json config
    try:
        from value_claw import config
        key = config.get_str("skills", "perplexity", "apiKey")
        if key:
            return key
    except Exception:
        pass
        
    print("Error: Perplexity API key not found. Set PERPLEXITY_API_KEY env var or add it to value_claw.json.", file=sys.stderr)
    sys.exit(1)

def search_perplexity(query: str, api_key: str) -> Dict[str, Any]:
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert research analyst. Provide detailed, accurate, and concise answers using the web. Always cite your sources."
            },
            {
                "role": "user",
                "content": query
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def main():
    if len(sys.argv) < 2:
        print("Usage: python perplexity.py <query>")
        sys.exit(1)
        
    query = sys.argv[1]
    api_key = get_api_key()
    
    try:
        results = search_perplexity(query, api_key)
        answer = results.get("choices", [])[0].get("message", {}).get("content", "No answer generated.")
        citations = results.get("citations", [])
        
        print(f"--- Perplexity Synthesized Answer for: '{query}' ---\n")
        print(answer)
        
        if citations:
            print("\n--- Citations ---")
            for i, cite in enumerate(citations, 1):
                print(f"[{i}] {cite}")
                
    except Exception as e:
        print(f"Error executing Perplexity Search: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

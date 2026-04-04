#!/usr/bin/env python3
"""
Crypto Data CLI Tool
A comprehensive cryptocurrency data tool using free APIs.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Union

import requests


class CryptoAPI:
    """Main API client for cryptocurrency data."""

    def __init__(self):
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.alternative_base = "https://api.alternative.me"
        self.defillama_base = "https://api.llama.fi"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CryptoDataCLI/1.0'
        })

        # Common coin mappings (symbol -> coingecko_id)
        self.coin_mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'ADA': 'cardano',
            'SOL': 'solana',
            'DOT': 'polkadot',
            'AVAX': 'avalanche-2',
            'MATIC': 'matic-network',
            'ATOM': 'cosmos',
            'NEAR': 'near',
            'UNI': 'uniswap',
            'LINK': 'chainlink',
            'LTC': 'litecoin',
            'BCH': 'bitcoin-cash',
            'XRP': 'ripple',
            'DOGE': 'dogecoin',
            'SHIB': 'shiba-inu',
            'TRX': 'tron',
            'ALGO': 'algorand',
            'VET': 'vechain',
            'ICP': 'internet-computer',
            'FIL': 'filecoin',
            'AAVE': 'aave',
            'MKR': 'maker',
            'SUSHI': 'sushi',
            'COMP': 'compound-governance-token',
            'YFI': 'yearn-finance',
            'SNX': 'havven',
            'CRV': 'curve-dao-token',
            '1INCH': '1inch',
            'BAL': 'balancer',
            'RUNE': 'thorchain',
            'LUNA': 'terra-luna-2',
            'UST': 'terrausd',
            'OSMO': 'osmosis',
            'JUNO': 'juno-network',
            'SCRT': 'secret',
            'KAVA': 'kava',
            'BAND': 'band-protocol'
        }

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Make API request with error handling."""
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API Error: {e}")
            sys.exit(1)
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            sys.exit(1)

    def _resolve_coin_id(self, coin: str) -> str:
        """Convert coin symbol/name to CoinGecko ID."""
        coin = coin.upper()

        # Check direct mapping first
        if coin in self.coin_mapping:
            return self.coin_mapping[coin]

        # Try lowercase as ID (bitcoin, ethereum, etc.)
        coin_lower = coin.lower()

        # For common coins, try direct ID lookup
        test_url = f"{self.coingecko_base}/simple/price"
        try:
            response = self.session.get(test_url, params={
                'ids': coin_lower,
                'vs_currencies': 'usd'
            }, timeout=5)
            if response.status_code == 200 and response.json():
                return coin_lower
        except Exception:
            pass

        # Search for the coin
        search_url = f"{self.coingecko_base}/search"
        try:
            response = self.session.get(search_url, params={'query': coin}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('coins'):
                    # Return first match
                    return data['coins'][0]['id']
        except Exception:
            pass

        print(f"❌ Could not find coin: {coin}")
        print("💡 Try using full name (bitcoin) or common symbol (BTC)")
        sys.exit(1)

    def get_price(self, coin: str) -> Dict:
        """Get current price and market data for a coin."""
        coin_id = self._resolve_coin_id(coin)

        url = f"{self.coingecko_base}/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd',
            'include_market_cap': 'true',
            'include_24hr_vol': 'true',
            'include_24hr_change': 'true'
        }

        data = self._make_request(url, params)
        time.sleep(1)  # Rate limit

        if coin_id not in data:
            print(f"❌ No data found for {coin}")
            sys.exit(1)

        return data[coin_id]

    def get_top_coins(self, limit: int = 20) -> List[Dict]:
        """Get top cryptocurrencies by market cap."""
        url = f"{self.coingecko_base}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': min(limit, 250),  # API limit
            'page': 1,
            'sparkline': 'false'
        }

        data = self._make_request(url, params)
        time.sleep(1)  # Rate limit

        return data

    def get_fear_greed_index(self) -> Dict:
        """Get Crypto Fear & Greed Index."""
        url = f"{self.alternative_base}/fng/"
        params = {'limit': 1}

        data = self._make_request(url, params)

        if not data.get('data'):
            print("❌ No Fear & Greed data available")
            sys.exit(1)

        return data['data'][0]

    def get_trending(self) -> List[Dict]:
        """Get trending coins on CoinGecko."""
        url = f"{self.coingecko_base}/search/trending"

        data = self._make_request(url)
        time.sleep(1)  # Rate limit

        return data.get('coins', [])

    def get_history(self, coin: str, days: int) -> Dict:
        """Get historical price data for a coin."""
        coin_id = self._resolve_coin_id(coin)

        url = f"{self.coingecko_base}/coins/{coin_id}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': days
        }

        data = self._make_request(url, params)
        time.sleep(1)  # Rate limit

        return data

    def get_defi_protocols(self) -> List[Dict]:
        """Get top DeFi protocols by TVL."""
        url = f"{self.defillama_base}/protocols"

        data = self._make_request(url)

        # Sort by TVL and take top 20
        sorted_protocols = sorted(data, key=lambda x: x.get('tvl', 0), reverse=True)
        return sorted_protocols[:20]


def format_number(num: Union[int, float], prefix: str = "") -> str:
    """Format large numbers with appropriate suffixes."""
    if num is None:
        return "N/A"

    if num >= 1e12:
        return f"{prefix}{num/1e12:.2f}T"
    elif num >= 1e9:
        return f"{prefix}{num/1e9:.2f}B"
    elif num >= 1e6:
        return f"{prefix}{num/1e6:.2f}M"
    elif num >= 1e3:
        return f"{prefix}{num/1e3:.2f}K"
    else:
        return f"{prefix}{num:.2f}"


def format_percentage(pct: Optional[float]) -> str:
    """Format percentage with emoji indicator."""
    if pct is None:
        return "N/A"

    emoji = "🟢" if pct >= 0 else "🔴"
    sign = "+" if pct >= 0 else ""
    return f"{emoji} {sign}{pct:.2f}%"


def format_timestamp(timestamp_ms: int) -> str:
    """Format timestamp for display."""
    dt = datetime.fromtimestamp(timestamp_ms / 1000)
    return dt.strftime("%Y-%m-%d %H:%M")


def cmd_price(args, api: CryptoAPI):
    """Handle price command."""
    data = api.get_price(args.coin)

    coin_name = args.coin.upper()
    price = data.get('usd', 0)
    market_cap = data.get('usd_market_cap', 0)
    volume = data.get('usd_24h_vol', 0)
    change = data.get('usd_24h_change', 0)

    print(f"💰 {coin_name} Price Data")
    print("=" * 40)
    print(f"💵 Price: ${price:,.2f}")
    print(f"📊 Market Cap: {format_number(market_cap, '$')}")
    print(f"📈 24h Volume: {format_number(volume, '$')}")
    print(f"📋 24h Change: {format_percentage(change)}")


def cmd_top(args, api: CryptoAPI):
    """Handle top command."""
    data = api.get_top_coins(args.limit)

    print(f"🏆 Top {len(data)} Cryptocurrencies by Market Cap")
    print("=" * 60)
    print(f"{'Rank':<4} {'Name':<20} {'Price':<12} {'Change':<10} {'Market Cap':<12}")
    print("-" * 60)

    for coin in data:
        rank = coin.get('market_cap_rank', 0)
        name = coin.get('name', 'Unknown')[:18]
        symbol = coin.get('symbol', '').upper()
        price = coin.get('current_price', 0)
        change = coin.get('price_change_percentage_24h', 0)
        market_cap = coin.get('market_cap', 0)

        change_emoji = "🟢" if change >= 0 else "🔴"
        change_str = f"{change_emoji}{change:+.1f}%"

        print(f"{rank:<4} {name} ({symbol})")
        print(f"     ${price:<11.2f} {change_str:<10} {format_number(market_cap, '$'):<12}")


def cmd_feargreed(args, api: CryptoAPI):
    """Handle feargreed command."""
    data = api.get_fear_greed_index()

    value = int(data.get('value', 0))
    classification = data.get('value_classification', 'Unknown')
    timestamp = data.get('timestamp', '')

    # Emoji based on fear/greed level
    if value <= 20:
        emoji = "😨"  # Extreme Fear
    elif value <= 40:
        emoji = "😟"  # Fear
    elif value <= 60:
        emoji = "😐"  # Neutral
    elif value <= 80:
        emoji = "😄"  # Greed
    else:
        emoji = "🤑"  # Extreme Greed

    print("😱 Crypto Fear & Greed Index")
    print("=" * 40)
    print(f"{emoji} Value: {value}/100")
    print(f"📊 Classification: {classification}")
    if timestamp:
        print(f"⏰ Last Updated: {timestamp}")


def cmd_trending(args, api: CryptoAPI):
    """Handle trending command."""
    data = api.get_trending()

    print("🔥 Trending Cryptocurrencies")
    print("=" * 40)

    for i, coin_data in enumerate(data[:10], 1):
        coin = coin_data.get('item', {})
        name = coin.get('name', 'Unknown')
        symbol = coin.get('symbol', 'Unknown').upper()
        rank = coin.get('market_cap_rank', 'N/A')

        print(f"{i:2d}. {name} ({symbol}) - Rank #{rank}")


def cmd_history(args, api: CryptoAPI):
    """Handle history command."""
    data = api.get_history(args.coin, args.days)

    prices = data.get('prices', [])
    if not prices:
        print(f"❌ No historical data found for {args.coin}")
        return

    # Get first and last prices for period analysis
    first_price = prices[0][1]
    last_price = prices[-1][1]
    price_change = ((last_price - first_price) / first_price) * 100

    # Get highest and lowest prices
    price_values = [p[1] for p in prices]
    highest = max(price_values)
    lowest = min(price_values)

    coin_name = args.coin.upper()

    print(f"📈 {coin_name} Price History ({args.days} days)")
    print("=" * 50)
    print(f"💵 Current Price: ${last_price:.2f}")
    print(f"📊 Period Change: {format_percentage(price_change)}")
    print(f"🔝 Highest: ${highest:.2f}")
    print(f"🔻 Lowest: ${lowest:.2f}")
    print(f"📋 Volatility: {((highest - lowest) / lowest * 100):.1f}%")

    # Show recent data points (last 5)
    print("\n⏰ Recent Prices:")
    for price_data in prices[-5:]:
        timestamp = format_timestamp(price_data[0])
        price = price_data[1]
        print(f"   {timestamp}: ${price:.2f}")


def cmd_defi(args, api: CryptoAPI):
    """Handle defi command."""
    data = api.get_defi_protocols()

    total_tvl = sum(p.get('tvl', 0) for p in data)

    print("🏦 Top DeFi Protocols by TVL")
    print("=" * 50)
    print(f"💰 Total TVL: {format_number(total_tvl, '$')}")
    print()
    print(f"{'Rank':<4} {'Protocol':<20} {'TVL':<12} {'Change':<10}")
    print("-" * 50)

    for i, protocol in enumerate(data, 1):
        name = protocol.get('name', 'Unknown')[:18]
        tvl = protocol.get('tvl', 0)
        change = protocol.get('change_1d', 0)

        change_emoji = "🟢" if change >= 0 else "🔴"
        change_str = f"{change_emoji}{change:+.1f}%" if change else "N/A"

        print(f"{i:<4} {name:<20} {format_number(tvl, '$'):<12} {change_str:<10}")


def main():
    parser = argparse.ArgumentParser(
        description="Cryptocurrency Data CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Price command
    price_parser = subparsers.add_parser('price', help='Get current price and market data')
    price_parser.add_argument('coin', help='Coin symbol (BTC) or name (bitcoin)')

    # Top command
    top_parser = subparsers.add_parser('top', help='Top cryptocurrencies by market cap')
    top_parser.add_argument('limit', nargs='?', type=int, default=20,
                           help='Number of coins to show (default: 20)')

    # Fear & Greed command
    subparsers.add_parser('feargreed', help='Crypto Fear & Greed Index')

    # Trending command
    subparsers.add_parser('trending', help='Trending cryptocurrencies')

    # History command
    history_parser = subparsers.add_parser('history', help='Historical price data')
    history_parser.add_argument('coin', help='Coin symbol (BTC) or name (bitcoin)')
    history_parser.add_argument('--days', type=int, default=30,
                               choices=[7, 30, 90, 365],
                               help='Number of days (7, 30, 90, 365)')

    # DeFi command
    subparsers.add_parser('defi', help='Top DeFi protocols by TVL')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    api = CryptoAPI()

    try:
        if args.command == 'price':
            cmd_price(args, api)
        elif args.command == 'top':
            cmd_top(args, api)
        elif args.command == 'feargreed':
            cmd_feargreed(args, api)
        elif args.command == 'trending':
            cmd_trending(args, api)
        elif args.command == 'history':
            cmd_history(args, api)
        elif args.command == 'defi':
            cmd_defi(args, api)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

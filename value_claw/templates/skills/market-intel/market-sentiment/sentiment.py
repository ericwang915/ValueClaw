#!/usr/bin/env python3
"""
Market Sentiment Analysis Tool
Provides various market sentiment indicators and a composite dashboard.
"""

import argparse
import sys
import warnings
from datetime import datetime
from typing import Any, Dict

import requests
import yfinance as yf

# Suppress yfinance warnings
warnings.filterwarnings("ignore", module="yfinance")


class SentimentAnalyzer:
    """Market sentiment analysis with multiple indicators."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_fear_greed_index(self) -> Dict[str, Any]:
        """Fetch CNN Fear & Greed Index."""
        try:
            url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            current = data['fear_and_greed']['score']
            timestamp = data['fear_and_greed']['timestamp']

            # Classification based on CNN's scale
            if current >= 75:
                classification = "Extreme Greed"
                emoji = "🔴"
            elif current >= 55:
                classification = "Greed"
                emoji = "🟡"
            elif current >= 45:
                classification = "Neutral"
                emoji = "🟡"
            elif current >= 25:
                classification = "Fear"
                emoji = "🟡"
            else:
                classification = "Extreme Fear"
                emoji = "🟢"

            return {
                'value': current,
                'classification': classification,
                'emoji': emoji,
                'timestamp': timestamp,
                'status': 'success'
            }
        except Exception as e:
            return {
                'value': None,
                'classification': 'Data Unavailable',
                'emoji': '⚪',
                'error': str(e),
                'status': 'error'
            }

    def get_vix_data(self) -> Dict[str, Any]:
        """Fetch VIX data with 20-day SMA."""
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="1mo", interval="1d")

            if hist.empty:
                raise ValueError("No VIX data available")

            current_vix = hist['Close'].iloc[-1]
            sma_20 = hist['Close'].tail(20).mean()

            # VIX interpretation (lower is better for sentiment)
            if current_vix >= 30:
                classification = "High Volatility"
                emoji = "🔴"
            elif current_vix >= 20:
                classification = "Elevated Volatility"
                emoji = "🟡"
            else:
                classification = "Low Volatility"
                emoji = "🟢"

            # Normalized score (inverse, since low VIX is good)
            score = max(0, min(100, 100 - (current_vix * 2)))

            return {
                'current': round(current_vix, 2),
                'sma_20': round(sma_20, 2),
                'score': round(score, 1),
                'classification': classification,
                'emoji': emoji,
                'status': 'success'
            }
        except Exception as e:
            return {
                'current': None,
                'sma_20': None,
                'score': None,
                'classification': 'Data Unavailable',
                'emoji': '⚪',
                'error': str(e),
                'status': 'error'
            }

    def get_market_breadth(self) -> Dict[str, Any]:
        """Analyze market breadth using SPY, QQQ, IWM."""
        try:
            tickers = ['SPY', 'QQQ', 'IWM']
            data = {}
            scores = []

            for ticker in tickers:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1mo", interval="1d")

                if hist.empty:
                    continue

                current = hist['Close'].iloc[-1]
                sma_10 = hist['Close'].tail(10).mean()
                sma_20 = hist['Close'].tail(20).mean()

                # Score based on price vs moving averages
                score = 0
                if current > sma_10:
                    score += 50
                if current > sma_20:
                    score += 50

                data[ticker] = {
                    'current': round(current, 2),
                    'sma_10': round(sma_10, 2),
                    'sma_20': round(sma_20, 2),
                    'score': score
                }
                scores.append(score)

            if not scores:
                raise ValueError("No market data available")

            avg_score = sum(scores) / len(scores)

            if avg_score >= 75:
                classification = "Strong Breadth"
                emoji = "🟢"
            elif avg_score >= 50:
                classification = "Moderate Breadth"
                emoji = "🟡"
            else:
                classification = "Weak Breadth"
                emoji = "🔴"

            return {
                'tickers': data,
                'average_score': round(avg_score, 1),
                'classification': classification,
                'emoji': emoji,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tickers': {},
                'average_score': None,
                'classification': 'Data Unavailable',
                'emoji': '⚪',
                'error': str(e),
                'status': 'error'
            }

    def get_put_call_ratio(self) -> Dict[str, Any]:
        """Estimate put/call ratio using SPY options."""
        try:
            spy = yf.Ticker("SPY")
            expirations = spy.options

            if not expirations:
                raise ValueError("No options data available")

            # Use nearest expiration
            exp_date = expirations[0]
            options_data = spy.option_chain(exp_date)

            calls = options_data.calls
            puts = options_data.puts

            if calls.empty or puts.empty:
                raise ValueError("Insufficient options data")

            # Calculate volume-weighted put/call ratio
            call_volume = calls['volume'].fillna(0).sum()
            put_volume = puts['volume'].fillna(0).sum()

            if call_volume == 0:
                ratio = float('inf')
            else:
                ratio = put_volume / call_volume

            # Interpretation (higher ratio = more bearish)
            if ratio >= 1.2:
                classification = "Bearish Sentiment"
                emoji = "🔴"
                score = 25
            elif ratio >= 0.8:
                classification = "Neutral Sentiment"
                emoji = "🟡"
                score = 50
            else:
                classification = "Bullish Sentiment"
                emoji = "🟢"
                score = 75

            return {
                'ratio': round(ratio, 3) if ratio != float('inf') else 'N/A',
                'put_volume': int(put_volume),
                'call_volume': int(call_volume),
                'score': score,
                'classification': classification,
                'emoji': emoji,
                'expiration': exp_date,
                'status': 'success'
            }
        except Exception as e:
            return {
                'ratio': None,
                'put_volume': None,
                'call_volume': None,
                'score': None,
                'classification': 'Data Unavailable',
                'emoji': '⚪',
                'error': str(e),
                'status': 'error'
            }

    def get_composite_score(self) -> Dict[str, Any]:
        """Calculate weighted composite sentiment score."""
        try:
            # Get all indicators
            fear_greed = self.get_fear_greed_index()
            vix = self.get_vix_data()
            breadth = self.get_market_breadth()
            put_call = self.get_put_call_ratio()

            scores = []
            weights = []
            details = {}

            # Fear & Greed Index (weight: 30%)
            if fear_greed['status'] == 'success':
                scores.append(fear_greed['value'])
                weights.append(0.3)
                details['fear_greed'] = fear_greed

            # VIX (weight: 25%)
            if vix['status'] == 'success' and vix['score'] is not None:
                scores.append(vix['score'])
                weights.append(0.25)
                details['vix'] = vix

            # Market Breadth (weight: 25%)
            if breadth['status'] == 'success' and breadth['average_score'] is not None:
                scores.append(breadth['average_score'])
                weights.append(0.25)
                details['breadth'] = breadth

            # Put/Call Ratio (weight: 20%)
            if put_call['status'] == 'success' and put_call['score'] is not None:
                scores.append(put_call['score'])
                weights.append(0.2)
                details['put_call'] = put_call

            if not scores:
                raise ValueError("No valid indicators available")

            # Normalize weights
            total_weight = sum(weights)
            normalized_weights = [w / total_weight for w in weights]

            # Calculate weighted average
            composite = sum(s * w for s, w in zip(scores, normalized_weights))

            # Classification
            if composite >= 70:
                classification = "Bullish"
                emoji = "🟢"
            elif composite >= 55:
                classification = "Moderately Bullish"
                emoji = "🟡"
            elif composite >= 45:
                classification = "Neutral"
                emoji = "🟡"
            elif composite >= 30:
                classification = "Moderately Bearish"
                emoji = "🟡"
            else:
                classification = "Bearish"
                emoji = "🔴"

            return {
                'score': round(composite, 1),
                'classification': classification,
                'emoji': emoji,
                'details': details,
                'indicators_used': len(scores),
                'status': 'success'
            }
        except Exception as e:
            return {
                'score': None,
                'classification': 'Unable to Calculate',
                'emoji': '⚪',
                'error': str(e),
                'status': 'error'
            }


def print_gauge(value: float, width: int = 50) -> str:
    """Create a text-based gauge visualization."""
    if value is None:
        return "⚪" * width

    filled = int((value / 100) * width)
    if value >= 70:
        fill_char = "🟢"
    elif value >= 55:
        fill_char = "🟡"
    elif value >= 30:
        fill_char = "🟡"
    else:
        fill_char = "🔴"

    gauge = fill_char * filled + "⚪" * (width - filled)
    return f"{gauge} {value}%"


def format_dashboard(analyzer: SentimentAnalyzer) -> str:
    """Format the complete dashboard."""
    composite = analyzer.get_composite_score()

    output = [
        "📊 MARKET SENTIMENT DASHBOARD",
        "=" * 50,
        f"🎯 COMPOSITE SCORE: {composite['emoji']} {composite['score'] or 'N/A'} - {composite['classification']}",
    ]

    if composite['score'] is not None:
        output.append(f"   {print_gauge(composite['score'])}")

    output.extend([
        "",
        "📈 INDIVIDUAL INDICATORS:",
        "-" * 30
    ])

    # Fear & Greed Index
    if 'fear_greed' in composite.get('details', {}):
        fg = composite['details']['fear_greed']
        output.append(f"😨 Fear & Greed: {fg['emoji']} {fg['value']} - {fg['classification']}")
    else:
        fg = analyzer.get_fear_greed_index()
        output.append(f"😨 Fear & Greed: {fg['emoji']} {fg.get('value', 'N/A')} - {fg['classification']}")

    # VIX
    if 'vix' in composite.get('details', {}):
        vix = composite['details']['vix']
        output.append(f"📊 VIX: {vix['emoji']} {vix['current']} (20-day: {vix['sma_20']}) - {vix['classification']}")
    else:
        vix = analyzer.get_vix_data()
        current = vix.get('current', 'N/A')
        sma = vix.get('sma_20', 'N/A')
        output.append(f"📊 VIX: {vix['emoji']} {current} (20-day: {sma}) - {vix['classification']}")

    # Market Breadth
    if 'breadth' in composite.get('details', {}):
        breadth = composite['details']['breadth']
        output.append(f"📏 Market Breadth: {breadth['emoji']} {breadth['average_score']}% - {breadth['classification']}")
        for ticker, data in breadth['tickers'].items():
            output.append(f"   {ticker}: ${data['current']} (10d: ${data['sma_10']}, 20d: ${data['sma_20']})")
    else:
        breadth = analyzer.get_market_breadth()
        output.append(f"📏 Market Breadth: {breadth['emoji']} {breadth.get('average_score', 'N/A')}% - {breadth['classification']}")

    # Put/Call Ratio
    if 'put_call' in composite.get('details', {}):
        pc = composite['details']['put_call']
        output.append(f"⚖️  Put/Call Ratio: {pc['emoji']} {pc['ratio']} - {pc['classification']}")
        output.append(f"   Puts: {pc['put_volume']:,}, Calls: {pc['call_volume']:,}")
    else:
        pc = analyzer.get_put_call_ratio()
        ratio = pc.get('ratio', 'N/A')
        puts = pc.get('put_volume', 'N/A')
        calls = pc.get('call_volume', 'N/A')
        output.append(f"⚖️  Put/Call Ratio: {pc['emoji']} {ratio} - {pc['classification']}")
        if puts != 'N/A' and calls != 'N/A':
            output.append(f"   Puts: {puts:,}, Calls: {calls:,}")

    output.extend([
        "",
        f"⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    ])

    return "\n".join(output)


def cmd_dashboard(args):
    """Show complete sentiment dashboard."""
    analyzer = SentimentAnalyzer()
    print(format_dashboard(analyzer))


def cmd_feargreed(args):
    """Show Fear & Greed Index only."""
    analyzer = SentimentAnalyzer()
    data = analyzer.get_fear_greed_index()

    print("😨 CNN Fear & Greed Index")
    print(f"Value: {data['emoji']} {data.get('value', 'N/A')}")
    print(f"Classification: {data['classification']}")

    if data['status'] == 'error':
        print(f"Error: {data.get('error', 'Unknown error')}")


def cmd_vix(args):
    """Show VIX data only."""
    analyzer = SentimentAnalyzer()
    data = analyzer.get_vix_data()

    print("📊 VIX (Volatility Index)")
    print(f"Current: {data['emoji']} {data.get('current', 'N/A')}")
    print(f"20-day SMA: {data.get('sma_20', 'N/A')}")
    print(f"Classification: {data['classification']}")

    if data['status'] == 'error':
        print(f"Error: {data.get('error', 'Unknown error')}")


def cmd_breadth(args):
    """Show market breadth only."""
    analyzer = SentimentAnalyzer()
    data = analyzer.get_market_breadth()

    print("📏 Market Breadth Analysis")
    print(f"Average Score: {data['emoji']} {data.get('average_score', 'N/A')}%")
    print(f"Classification: {data['classification']}")

    if data['status'] == 'success' and data['tickers']:
        print("\nTicker Details:")
        for ticker, info in data['tickers'].items():
            print(f"  {ticker}: ${info['current']} (10d: ${info['sma_10']}, 20d: ${info['sma_20']})")
    elif data['status'] == 'error':
        print(f"Error: {data.get('error', 'Unknown error')}")


def cmd_putcall(args):
    """Show put/call ratio only."""
    analyzer = SentimentAnalyzer()
    data = analyzer.get_put_call_ratio()

    print("⚖️  Put/Call Ratio")
    print(f"Ratio: {data['emoji']} {data.get('ratio', 'N/A')}")
    print(f"Classification: {data['classification']}")

    if data['status'] == 'success':
        puts = data.get('put_volume', 'N/A')
        calls = data.get('call_volume', 'N/A')
        exp = data.get('expiration', 'N/A')
        print(f"Put Volume: {puts:,}" if puts != 'N/A' else f"Put Volume: {puts}")
        print(f"Call Volume: {calls:,}" if calls != 'N/A' else f"Call Volume: {calls}")
        print(f"Expiration: {exp}")
    elif data['status'] == 'error':
        print(f"Error: {data.get('error', 'Unknown error')}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Market Sentiment Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s dashboard     # Show all indicators
  %(prog)s feargreed     # Show Fear & Greed Index only
  %(prog)s vix          # Show VIX data only
  %(prog)s breadth      # Show market breadth only
  %(prog)s putcall      # Show put/call ratio only
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Dashboard command
    parser_dashboard = subparsers.add_parser('dashboard', help='Show complete sentiment dashboard')
    parser_dashboard.set_defaults(func=cmd_dashboard)

    # Fear & Greed command
    parser_fg = subparsers.add_parser('feargreed', help='Show CNN Fear & Greed Index')
    parser_fg.set_defaults(func=cmd_feargreed)

    # VIX command
    parser_vix = subparsers.add_parser('vix', help='Show VIX volatility data')
    parser_vix.set_defaults(func=cmd_vix)

    # Breadth command
    parser_breadth = subparsers.add_parser('breadth', help='Show market breadth analysis')
    parser_breadth.set_defaults(func=cmd_breadth)

    # Put/Call command
    parser_pc = subparsers.add_parser('putcall', help='Show put/call ratio')
    parser_pc.set_defaults(func=cmd_putcall)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

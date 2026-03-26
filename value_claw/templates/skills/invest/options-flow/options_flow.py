#!/usr/bin/env python3
"""
Options Flow CLI Tool
A comprehensive options analysis tool using yfinance.
"""

import argparse
import sys
import warnings
from datetime import datetime
from typing import List, Tuple

try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError as e:
    print(f"Error: Required package not installed: {e}")
    print("Install with: pip install yfinance pandas numpy")
    sys.exit(1)

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')


class OptionsAnalyzer:
    """Main class for options analysis functionality."""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)

    def get_current_price(self) -> float:
        """Get current stock price."""
        try:
            hist = self.stock.history(period="1d", interval="1m")
            if hist.empty:
                # Fallback to daily data
                hist = self.stock.history(period="5d")
            return float(hist['Close'].iloc[-1])
        except Exception as e:
            raise ValueError(f"Could not fetch current price for {self.ticker}: {e}")

    def get_options_expirations(self) -> List[str]:
        """Get available options expiration dates."""
        try:
            return list(self.stock.options)
        except Exception as e:
            raise ValueError(f"Could not fetch options expirations for {self.ticker}: {e}")

    def get_options_chain(self, expiry: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Get options chain for a specific expiry."""
        try:
            opt_chain = self.stock.option_chain(expiry)
            return opt_chain.calls, opt_chain.puts
        except Exception as e:
            raise ValueError(f"Could not fetch options chain for {self.ticker} expiry {expiry}: {e}")

    def find_nearest_expiry(self) -> str:
        """Find the nearest expiration date."""
        expirations = self.get_options_expirations()
        if not expirations:
            raise ValueError(f"No options available for {self.ticker}")

        today = datetime.now().date()
        nearest = min(expirations, key=lambda x: abs((datetime.strptime(x, '%Y-%m-%d').date() - today).days))
        return nearest

    def find_atm_options(self, calls: pd.DataFrame, puts: pd.DataFrame, current_price: float) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Find options closest to current price (ATM) and return top 10 on each side."""
        # Find strikes around current price
        calls_filtered = calls[calls['strike'] >= current_price * 0.8]
        puts_filtered = puts[puts['strike'] <= current_price * 1.2]

        # Sort by distance from current price and take top 10
        calls_filtered['distance'] = abs(calls_filtered['strike'] - current_price)
        puts_filtered['distance'] = abs(puts_filtered['strike'] - current_price)

        calls_top = calls_filtered.nsmallest(10, 'distance')
        puts_top = puts_filtered.nsmallest(10, 'distance')

        return calls_top, puts_top

    def format_options_table(self, options_df: pd.DataFrame, option_type: str) -> str:
        """Format options data into a readable table."""
        if options_df.empty:
            return f"No {option_type} data available\n"

        # Select and rename columns for display
        display_cols = ['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']
        available_cols = [col for col in display_cols if col in options_df.columns]

        if not available_cols:
            return f"No {option_type} data available\n"

        df = options_df[available_cols].copy()

        # Format columns
        if 'strike' in df.columns:
            df['strike'] = df['strike'].apply(lambda x: f"${x:.2f}")
        if 'lastPrice' in df.columns:
            df['lastPrice'] = df['lastPrice'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        if 'bid' in df.columns:
            df['bid'] = df['bid'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        if 'ask' in df.columns:
            df['ask'] = df['ask'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        if 'volume' in df.columns:
            df['volume'] = df['volume'].fillna(0).astype(int)
        if 'openInterest' in df.columns:
            df['openInterest'] = df['openInterest'].fillna(0).astype(int)
        if 'impliedVolatility' in df.columns:
            df['impliedVolatility'] = df['impliedVolatility'].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")

        # Rename columns for display
        column_names = {
            'strike': 'Strike',
            'lastPrice': 'Last',
            'bid': 'Bid',
            'ask': 'Ask',
            'volume': 'Volume',
            'openInterest': 'OI',
            'impliedVolatility': 'IV'
        }
        df = df.rename(columns=column_names)

        return f"\n{option_type.upper()}:\n{df.to_string(index=False)}\n"


def cmd_chain(args):
    """Handle the chain subcommand."""
    try:
        analyzer = OptionsAnalyzer(args.ticker)
        current_price = analyzer.get_current_price()

        # Determine expiry
        if args.expiry:
            expiry = args.expiry
            # Validate expiry format and availability
            available_expiries = analyzer.get_options_expirations()
            if expiry not in available_expiries:
                print(f"Error: Expiry {expiry} not available for {args.ticker}")
                print(f"Available expiries: {', '.join(available_expiries[:5])}...")
                return
        else:
            expiry = analyzer.find_nearest_expiry()

        print(f"\nOptions Chain for {args.ticker}")
        print(f"Current Price: ${current_price:.2f}")
        print(f"Expiration: {expiry}")
        print("=" * 70)

        # Get options chain
        calls, puts = analyzer.get_options_chain(expiry)

        if calls.empty and puts.empty:
            print("No options data available for this expiry")
            return

        # Find ATM options
        calls_atm, puts_atm = analyzer.find_atm_options(calls, puts, current_price)

        # Display results
        print(analyzer.format_options_table(calls_atm, "calls"))
        print(analyzer.format_options_table(puts_atm, "puts"))

    except Exception as e:
        print(f"Error: {e}")


def cmd_unusual(args):
    """Handle the unusual subcommand - detect unusual activity."""
    try:
        analyzer = OptionsAnalyzer(args.ticker)
        current_price = analyzer.get_current_price()

        print(f"\nUnusual Options Activity for {args.ticker}")
        print(f"Current Price: ${current_price:.2f}")
        print("Scanning for volume > 5x open interest...")
        print("=" * 70)

        unusual_options = []

        # Check all available expiries
        expiries = analyzer.get_options_expirations()[:3]  # Limit to first 3 expiries for performance

        for expiry in expiries:
            try:
                calls, puts = analyzer.get_options_chain(expiry)

                # Check calls for unusual activity
                for _, row in calls.iterrows():
                    volume = row.get('volume', 0) or 0
                    oi = row.get('openInterest', 0) or 0
                    if oi > 0 and volume > 5 * oi:
                        ratio = volume / oi if oi > 0 else float('inf')
                        unusual_options.append({
                            'type': 'CALL',
                            'strike': row['strike'],
                            'expiry': expiry,
                            'volume': volume,
                            'oi': oi,
                            'ratio': ratio,
                            'lastPrice': row.get('lastPrice', 0),
                            'iv': row.get('impliedVolatility', 0)
                        })

                # Check puts for unusual activity
                for _, row in puts.iterrows():
                    volume = row.get('volume', 0) or 0
                    oi = row.get('openInterest', 0) or 0
                    if oi > 0 and volume > 5 * oi:
                        ratio = volume / oi if oi > 0 else float('inf')
                        unusual_options.append({
                            'type': 'PUT',
                            'strike': row['strike'],
                            'expiry': expiry,
                            'volume': volume,
                            'oi': oi,
                            'ratio': ratio,
                            'lastPrice': row.get('lastPrice', 0),
                            'iv': row.get('impliedVolatility', 0)
                        })

            except Exception as e:
                print(f"Warning: Could not process expiry {expiry}: {e}")
                continue

        if unusual_options:
            # Sort by volume/OI ratio
            unusual_options.sort(key=lambda x: x['ratio'], reverse=True)

            print("🔥 UNUSUAL ACTIVITY DETECTED 🔥\n")
            print(f"{'Type':<5} {'Strike':<8} {'Expiry':<12} {'Vol':<8} {'OI':<8} {'Ratio':<8} {'Last':<8} {'IV':<8}")
            print("-" * 70)

            for opt in unusual_options[:10]:  # Show top 10
                ratio_str = f"{opt['ratio']:.1f}x" if opt['ratio'] != float('inf') else "∞"
                iv_str = f"{opt['iv']:.1%}" if opt['iv'] and pd.notna(opt['iv']) else "N/A"
                last_str = f"${opt['lastPrice']:.2f}" if opt['lastPrice'] and pd.notna(opt['lastPrice']) else "N/A"

                print(f"🔥{opt['type']:<4} ${opt['strike']:<7.2f} {opt['expiry']:<12} {opt['volume']:<8} {opt['oi']:<8} {ratio_str:<8} {last_str:<8} {iv_str:<8}")
        else:
            print("No unusual activity detected (volume > 5x open interest)")

    except Exception as e:
        print(f"Error: {e}")


def cmd_maxpain(args):
    """Handle the maxpain subcommand - calculate max pain price."""
    try:
        analyzer = OptionsAnalyzer(args.ticker)
        current_price = analyzer.get_current_price()

        print(f"\nMax Pain Analysis for {args.ticker}")
        print(f"Current Price: ${current_price:.2f}")
        print("=" * 50)

        # Use nearest expiry for max pain calculation
        expiry = analyzer.find_nearest_expiry()
        calls, puts = analyzer.get_options_chain(expiry)

        if calls.empty and puts.empty:
            print("No options data available")
            return

        print(f"Calculating max pain for expiry: {expiry}")

        # Get all unique strikes
        all_strikes = set()
        if not calls.empty:
            all_strikes.update(calls['strike'].values)
        if not puts.empty:
            all_strikes.update(puts['strike'].values)

        all_strikes = sorted(list(all_strikes))

        max_pain_data = []

        for strike in all_strikes:
            total_pain = 0

            # Calculate pain from calls (ITM when stock > strike)
            calls_at_strike = calls[calls['strike'] <= strike]
            if not calls_at_strike.empty:
                for _, call in calls_at_strike.iterrows():
                    if strike > call['strike']:
                        pain = (strike - call['strike']) * call.get('openInterest', 0)
                        total_pain += pain

            # Calculate pain from puts (ITM when stock < strike)
            puts_at_strike = puts[puts['strike'] >= strike]
            if not puts_at_strike.empty:
                for _, put in puts_at_strike.iterrows():
                    if strike < put['strike']:
                        pain = (put['strike'] - strike) * put.get('openInterest', 0)
                        total_pain += pain

            max_pain_data.append({'strike': strike, 'total_pain': total_pain})

        if max_pain_data:
            # Find strike with minimum total pain
            max_pain_strike = min(max_pain_data, key=lambda x: x['total_pain'])

            print(f"\n🎯 Max Pain Price: ${max_pain_strike['strike']:.2f}")
            print(f"Distance from current: {((max_pain_strike['strike'] - current_price) / current_price) * 100:+.1f}%")
            print(f"Total pain at max pain: ${max_pain_strike['total_pain']:,.0f}")

            # Show top 5 strikes with lowest pain
            sorted_pain = sorted(max_pain_data, key=lambda x: x['total_pain'])[:5]
            print("\nTop 5 Low-Pain Strikes:")
            print(f"{'Strike':<10} {'Total Pain':<15}")
            print("-" * 25)
            for data in sorted_pain:
                print(f"${data['strike']:<9.2f} ${data['total_pain']:<14,.0f}")
        else:
            print("Could not calculate max pain - insufficient data")

    except Exception as e:
        print(f"Error: {e}")


def cmd_iv(args):
    """Handle the iv subcommand - IV rank analysis."""
    try:
        analyzer = OptionsAnalyzer(args.ticker)
        current_price = analyzer.get_current_price()

        print(f"\nImplied Volatility Rank for {args.ticker}")
        print(f"Current Price: ${current_price:.2f}")
        print("=" * 50)

        # Get nearest expiry options
        expiry = analyzer.find_nearest_expiry()
        calls, puts = analyzer.get_options_chain(expiry)

        # Find ATM options for current IV
        calls_atm, puts_atm = analyzer.find_atm_options(calls, puts, current_price)

        # Get current IV from ATM options
        current_iv_call = None
        current_iv_put = None

        if not calls_atm.empty:
            atm_call = calls_atm.iloc[0]
            current_iv_call = atm_call.get('impliedVolatility', None)

        if not puts_atm.empty:
            atm_put = puts_atm.iloc[0]
            current_iv_put = atm_put.get('impliedVolatility', None)

        # Use average of call and put IV, or whichever is available
        if current_iv_call and current_iv_put:
            current_iv = (current_iv_call + current_iv_put) / 2
        elif current_iv_call:
            current_iv = current_iv_call
        elif current_iv_put:
            current_iv = current_iv_put
        else:
            print("Could not determine current implied volatility")
            return

        print(f"Current IV: {current_iv:.1%}")
        print(f"Expiry analyzed: {expiry}")

        # Try to get historical volatility data for comparison
        try:
            # Get 1 year of historical data for volatility calculation
            hist = analyzer.stock.history(period="1y")
            if not hist.empty:
                # Calculate historical volatility (annualized)
                returns = hist['Close'].pct_change().dropna()
                historical_vol = returns.std() * np.sqrt(252)  # Annualized

                print(f"Historical Volatility (1Y): {historical_vol:.1%}")

                # Compare current IV to historical vol
                iv_premium = (current_iv - historical_vol) / historical_vol * 100 if historical_vol > 0 else 0
                print(f"IV Premium: {iv_premium:+.1f}%")

                if iv_premium > 20:
                    print("📈 IV is elevated (>20% above historical)")
                elif iv_premium < -20:
                    print("📉 IV is depressed (>20% below historical)")
                else:
                    print("📊 IV is near historical levels")

        except Exception as e:
            print(f"Note: Could not calculate historical volatility comparison: {e}")

        # Show IV across different strikes for context
        print(f"\nIV Across Strikes (Expiry: {expiry}):")
        if not calls_atm.empty:
            print("\nCALLS:")
            print(f"{'Strike':<10} {'IV':<10}")
            print("-" * 20)
            for _, row in calls_atm.head().iterrows():
                iv = row.get('impliedVolatility', 0)
                iv_str = f"{iv:.1%}" if iv and pd.notna(iv) else "N/A"
                print(f"${row['strike']:<9.2f} {iv_str:<10}")

        if not puts_atm.empty:
            print("\nPUTS:")
            print(f"{'Strike':<10} {'IV':<10}")
            print("-" * 20)
            for _, row in puts_atm.head().iterrows():
                iv = row.get('impliedVolatility', 0)
                iv_str = f"{iv:.1%}" if iv and pd.notna(iv) else "N/A"
                print(f"${row['strike']:<9.2f} {iv_str:<10}")

    except Exception as e:
        print(f"Error: {e}")


def cmd_pcr(args):
    """Handle the pcr subcommand - put/call ratio analysis."""
    try:
        analyzer = OptionsAnalyzer(args.ticker)
        current_price = analyzer.get_current_price()

        print(f"\nPut/Call Ratio Analysis for {args.ticker}")
        print(f"Current Price: ${current_price:.2f}")
        print("=" * 50)

        total_call_volume = 0
        total_put_volume = 0
        total_call_oi = 0
        total_put_oi = 0

        # Analyze multiple expiries for comprehensive PCR
        expiries = analyzer.get_options_expirations()[:3]  # First 3 expiries

        print("Analyzing expiries:", ", ".join(expiries))
        print()

        for expiry in expiries:
            try:
                calls, puts = analyzer.get_options_chain(expiry)

                # Sum volumes and open interest
                call_vol = calls['volume'].fillna(0).sum() if not calls.empty else 0
                put_vol = puts['volume'].fillna(0).sum() if not puts.empty else 0
                call_oi = calls['openInterest'].fillna(0).sum() if not calls.empty else 0
                put_oi = puts['openInterest'].fillna(0).sum() if not puts.empty else 0

                total_call_volume += call_vol
                total_put_volume += put_vol
                total_call_oi += call_oi
                total_put_oi += put_oi

                # Show per-expiry breakdown
                pcr_vol = put_vol / call_vol if call_vol > 0 else float('inf')
                pcr_oi = put_oi / call_oi if call_oi > 0 else float('inf')

                pcr_vol_str = f"{pcr_vol:.2f}" if pcr_vol != float('inf') else "N/A"
                pcr_oi_str = f"{pcr_oi:.2f}" if pcr_oi != float('inf') else "N/A"

                print(f"Expiry {expiry}:")
                print(f"  Volume PCR: {pcr_vol_str}")
                print(f"  OI PCR: {pcr_oi_str}")
                print(f"  Call Volume: {call_vol:,} | Put Volume: {put_vol:,}")
                print(f"  Call OI: {call_oi:,} | Put OI: {put_oi:,}")
                print()

            except Exception as e:
                print(f"Warning: Could not process expiry {expiry}: {e}")
                continue

        # Overall PCR
        overall_pcr_vol = total_put_volume / total_call_volume if total_call_volume > 0 else float('inf')
        overall_pcr_oi = total_put_oi / total_call_oi if total_call_oi > 0 else float('inf')

        print("=" * 50)
        print("OVERALL PUT/CALL RATIOS:")

        if overall_pcr_vol != float('inf'):
            print(f"📊 Volume PCR: {overall_pcr_vol:.2f}")
            if overall_pcr_vol > 1.0:
                print("   → Bearish sentiment (more put volume)")
            elif overall_pcr_vol < 0.7:
                print("   → Bullish sentiment (more call volume)")
            else:
                print("   → Neutral sentiment")
        else:
            print("📊 Volume PCR: N/A (no call volume)")

        if overall_pcr_oi != float('inf'):
            print(f"📈 Open Interest PCR: {overall_pcr_oi:.2f}")
            if overall_pcr_oi > 1.0:
                print("   → Bearish positioning (more put OI)")
            elif overall_pcr_oi < 0.7:
                print("   → Bullish positioning (more call OI)")
            else:
                print("   → Neutral positioning")
        else:
            print("📈 Open Interest PCR: N/A (no call OI)")

        print(f"\nTotal Call Volume: {total_call_volume:,}")
        print(f"Total Put Volume: {total_put_volume:,}")
        print(f"Total Call OI: {total_call_oi:,}")
        print(f"Total Put OI: {total_put_oi:,}")

    except Exception as e:
        print(f"Error: {e}")


def main():
    """Main function to set up argument parsing and route to commands."""
    parser = argparse.ArgumentParser(
        description="Options Flow Analysis CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s chain AAPL
  %(prog)s chain AAPL --expiry 2026-04-17
  %(prog)s unusual TSLA
  %(prog)s maxpain NVDA
  %(prog)s iv MSFT
  %(prog)s pcr SPY
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Chain command
    chain_parser = subparsers.add_parser('chain', help='Show options chain')
    chain_parser.add_argument('ticker', help='Stock ticker symbol')
    chain_parser.add_argument('--expiry', help='Specific expiration date (YYYY-MM-DD)')
    chain_parser.set_defaults(func=cmd_chain)

    # Unusual command
    unusual_parser = subparsers.add_parser('unusual', help='Detect unusual options activity')
    unusual_parser.add_argument('ticker', help='Stock ticker symbol')
    unusual_parser.set_defaults(func=cmd_unusual)

    # Max pain command
    maxpain_parser = subparsers.add_parser('maxpain', help='Calculate max pain price')
    maxpain_parser.add_argument('ticker', help='Stock ticker symbol')
    maxpain_parser.set_defaults(func=cmd_maxpain)

    # IV command
    iv_parser = subparsers.add_parser('iv', help='Implied volatility rank analysis')
    iv_parser.add_argument('ticker', help='Stock ticker symbol')
    iv_parser.set_defaults(func=cmd_iv)

    # PCR command
    pcr_parser = subparsers.add_parser('pcr', help='Put/call ratio analysis')
    pcr_parser.add_argument('ticker', help='Stock ticker symbol')
    pcr_parser.set_defaults(func=cmd_pcr)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

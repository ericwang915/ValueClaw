#!/usr/bin/env python3
"""
Institutional Holdings CLI Tool
Track institutional holdings, ownership patterns, and concentration metrics.
"""

import argparse
import sys
from typing import Optional

import pandas as pd
import requests
import yfinance as yf


class InstitutionalHoldingsCLI:
    """CLI tool for tracking institutional holdings and ownership patterns."""

    USER_AGENT = "ValueClaw/1.0 (investment research tool)"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.USER_AGENT})

    def get_ticker_info(self, ticker: str) -> Optional[yf.Ticker]:
        """Get ticker info with error handling."""
        try:
            stock = yf.Ticker(ticker.upper())
            # Test if ticker is valid by getting basic info
            info = stock.info
            if not info or 'regularMarketPrice' not in info:
                print(f"❌ Invalid ticker: {ticker}")
                return None
            return stock
        except Exception as e:
            print(f"❌ Error fetching data for {ticker}: {str(e)}")
            return None

    def format_number(self, value: float) -> str:
        """Format large numbers with appropriate suffixes."""
        if pd.isna(value) or value == 0:
            return "N/A"

        if abs(value) >= 1e9:
            return f"{value/1e9:.2f}B"
        elif abs(value) >= 1e6:
            return f"{value/1e6:.2f}M"
        elif abs(value) >= 1e3:
            return f"{value/1e3:.2f}K"
        else:
            return f"{value:.2f}"

    def format_percentage(self, value: float) -> str:
        """Format percentage values."""
        if pd.isna(value):
            return "N/A"
        return f"{value:.2f}%"

    def calculate_herfindahl_index(self, percentages: list) -> float:
        """Calculate Herfindahl-Hirschman Index for concentration."""
        # Remove NaN values and convert to decimals
        valid_percentages = [p/100 for p in percentages if not pd.isna(p)]
        if not valid_percentages:
            return 0.0

        # HHI = sum of squared market shares
        hhi = sum(p**2 for p in valid_percentages)
        return hhi * 10000  # Scale to 0-10000 range

    def cmd_holders(self, ticker: str) -> None:
        """Show top institutional holders for a ticker."""
        print(f"🏛️  Institutional Holders: {ticker.upper()}")
        print("=" * 70)

        stock = self.get_ticker_info(ticker)
        if not stock:
            return

        try:
            holders = stock.institutional_holders
            if holders is None or holders.empty:
                print("❌ No institutional holders data available")
                return

            # Format the data
            print(f"{'Institution':<30} {'Shares':<12} {'%':<8} {'Value':<12} {'Date':<12}")
            print("-" * 70)

            for _, row in holders.iterrows():
                institution = row.get('Holder', 'N/A')[:29]
                shares = self.format_number(row.get('Shares', 0))
                pct = self.format_percentage(row.get('% Out', 0))
                value = self.format_number(row.get('Value', 0))
                date_reported = row.get('Date Reported', 'N/A')

                if hasattr(date_reported, 'strftime'):
                    date_str = date_reported.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_reported)[:10]

                print(f"{institution:<30} {shares:<12} {pct:<8} {value:<12} {date_str:<12}")

            print(f"\n📊 Total institutions shown: {len(holders)}")

        except Exception as e:
            print(f"❌ Error retrieving institutional holders: {str(e)}")

    def cmd_ownership(self, ticker: str) -> None:
        """Show institutional ownership percentage and summary stats."""
        print(f"📈 Institutional Ownership: {ticker.upper()}")
        print("=" * 50)

        stock = self.get_ticker_info(ticker)
        if not stock:
            return

        try:
            # Get basic stock info
            info = stock.info
            shares_outstanding = info.get('sharesOutstanding', 0)
            float_shares = info.get('floatShares', shares_outstanding)

            # Get institutional holders
            inst_holders = stock.institutional_holders
            mutual_holders = stock.mutualfund_holders

            total_inst_shares = 0
            total_mutual_shares = 0

            if inst_holders is not None and not inst_holders.empty:
                total_inst_shares = inst_holders['Shares'].sum()

            if mutual_holders is not None and not mutual_holders.empty:
                total_mutual_shares = mutual_holders['Shares'].sum()

            # Calculate percentages
            inst_ownership_pct = (total_inst_shares / shares_outstanding * 100) if shares_outstanding > 0 else 0
            mutual_ownership_pct = (total_mutual_shares / shares_outstanding * 100) if shares_outstanding > 0 else 0
            total_institutional = inst_ownership_pct + mutual_ownership_pct

            # Display results
            print(f"Shares Outstanding:     {self.format_number(shares_outstanding)}")
            print(f"Float Shares:           {self.format_number(float_shares)}")
            print()
            print(f"Institutional Shares:   {self.format_number(total_inst_shares)}")
            print(f"Institutional %:        {self.format_percentage(inst_ownership_pct)}")
            print()
            print(f"Mutual Fund Shares:     {self.format_number(total_mutual_shares)}")
            print(f"Mutual Fund %:          {self.format_percentage(mutual_ownership_pct)}")
            print()
            print(f"Total Institutional:    {self.format_percentage(total_institutional)}")

            # Summary stats
            if inst_holders is not None and not inst_holders.empty:
                print("\n📊 Summary Stats:")
                print(f"Number of Institutions: {len(inst_holders)}")
                avg_holding = inst_holders['% Out'].mean() if '% Out' in inst_holders.columns else 0
                print(f"Average Holding:        {self.format_percentage(avg_holding)}")
                max_holding = inst_holders['% Out'].max() if '% Out' in inst_holders.columns else 0
                print(f"Largest Holding:        {self.format_percentage(max_holding)}")

        except Exception as e:
            print(f"❌ Error retrieving ownership data: {str(e)}")

    def cmd_fund(self, fund_name: str) -> None:
        """Search for a specific fund's holdings using yfinance data."""
        print(f"🔍 Fund Holdings Search: {fund_name}")
        print("=" * 60)

        # Note: Since SEC EDGAR API is complex and yfinance provides institutional
        # data, we'll search through available institutional holders data
        print(f"Searching for funds matching: '{fund_name}'...")

        try:
            # For demonstration, we'll search through some major tickers
            # In practice, you'd want to search across a broader universe
            sample_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BRK-B']

            found_holdings = []

            for ticker in sample_tickers:
                try:
                    stock = yf.Ticker(ticker)
                    inst_holders = stock.institutional_holders
                    mutual_holders = stock.mutualfund_holders

                    # Search in institutional holders
                    if inst_holders is not None:
                        matches = inst_holders[inst_holders['Holder'].str.contains(
                            fund_name, case=False, na=False)]
                        for _, row in matches.iterrows():
                            found_holdings.append({
                                'ticker': ticker,
                                'holder': row['Holder'],
                                'shares': row.get('Shares', 0),
                                'percentage': row.get('% Out', 0),
                                'value': row.get('Value', 0),
                                'type': 'Institutional'
                            })

                    # Search in mutual fund holders
                    if mutual_holders is not None:
                        matches = mutual_holders[mutual_holders['Holder'].str.contains(
                            fund_name, case=False, na=False)]
                        for _, row in matches.iterrows():
                            found_holdings.append({
                                'ticker': ticker,
                                'holder': row['Holder'],
                                'shares': row.get('Shares', 0),
                                'percentage': row.get('% Out', 0),
                                'value': row.get('Value', 0),
                                'type': 'Mutual Fund'
                            })

                except Exception:
                    continue  # Skip tickers with errors

            if found_holdings:
                print(f"\n📋 Holdings Found ({len(found_holdings)} positions):")
                print(f"{'Ticker':<8} {'Type':<12} {'Holder':<25} {'%':<8} {'Value':<12}")
                print("-" * 70)

                for holding in found_holdings:
                    ticker = holding['ticker']
                    holder_type = holding['type']
                    holder = holding['holder'][:24]
                    pct = self.format_percentage(holding['percentage'])
                    value = self.format_number(holding['value'])

                    print(f"{ticker:<8} {holder_type:<12} {holder:<25} {pct:<8} {value:<12}")

                total_value = sum(h['value'] for h in found_holdings if not pd.isna(h['value']))
                print(f"\n💰 Total Portfolio Value: {self.format_number(total_value)}")

            else:
                print(f"❌ No holdings found for fund: '{fund_name}'")
                print("💡 Try searching with partial names (e.g., 'Vanguard', 'BlackRock', 'Fidelity')")

        except Exception as e:
            print(f"❌ Error searching for fund: {str(e)}")

    def cmd_concentration(self, ticker: str) -> None:
        """Calculate concentration metrics for top holders."""
        print(f"📊 Ownership Concentration: {ticker.upper()}")
        print("=" * 50)

        stock = self.get_ticker_info(ticker)
        if not stock:
            return

        try:
            holders = stock.institutional_holders
            if holders is None or holders.empty:
                print("❌ No institutional holders data available")
                return

            # Get top 10 holders
            top_holders = holders.head(10)
            percentages = top_holders['% Out'].tolist()

            # Calculate HHI
            hhi = self.calculate_herfindahl_index(percentages)

            # Display top holders
            print("🏆 Top 10 Institutional Holders:")
            print(f"{'Rank':<5} {'Institution':<30} {'% of Shares':<12}")
            print("-" * 50)

            for i, (_, row) in enumerate(top_holders.iterrows(), 1):
                institution = row['Holder'][:29]
                pct = self.format_percentage(row['% Out'])
                print(f"{i:<5} {institution:<30} {pct:<12}")

            # Concentration metrics
            total_top10 = top_holders['% Out'].sum()
            top5_pct = top_holders.head(5)['% Out'].sum()
            top1_pct = top_holders.iloc[0]['% Out'] if len(top_holders) > 0 else 0

            print("\n📈 Concentration Metrics:")
            print(f"Top 1 Holder:           {self.format_percentage(top1_pct)}")
            print(f"Top 5 Holders:          {self.format_percentage(top5_pct)}")
            print(f"Top 10 Holders:         {self.format_percentage(total_top10)}")
            print(f"Herfindahl Index (HHI): {hhi:.0f}")

            # HHI interpretation
            print("\n📋 Concentration Level:")
            if hhi < 1500:
                print("🟢 Low concentration (competitive)")
            elif hhi < 2500:
                print("🟡 Moderate concentration")
            else:
                print("🔴 High concentration")

        except Exception as e:
            print(f"❌ Error calculating concentration: {str(e)}")

    def run(self):
        """Main CLI entry point."""
        parser = argparse.ArgumentParser(
            description="Institutional Holdings CLI Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s holders AAPL           # Show top institutional holders
  %(prog)s ownership TSLA         # Show institutional ownership stats
  %(prog)s fund "BlackRock"       # Search for BlackRock holdings
  %(prog)s concentration MSFT     # Calculate ownership concentration
            """)

        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # holders command
        holders_parser = subparsers.add_parser('holders', help='Show top institutional holders')
        holders_parser.add_argument('ticker', help='Stock ticker symbol')

        # ownership command
        ownership_parser = subparsers.add_parser('ownership', help='Show institutional ownership stats')
        ownership_parser.add_argument('ticker', help='Stock ticker symbol')

        # fund command
        fund_parser = subparsers.add_parser('fund', help='Search for specific fund holdings')
        fund_parser.add_argument('fund_name', help='Fund name to search for')

        # concentration command
        concentration_parser = subparsers.add_parser('concentration', help='Calculate ownership concentration')
        concentration_parser.add_argument('ticker', help='Stock ticker symbol')

        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            return

        # Execute the appropriate command
        try:
            if args.command == 'holders':
                self.cmd_holders(args.ticker)
            elif args.command == 'ownership':
                self.cmd_ownership(args.ticker)
            elif args.command == 'fund':
                self.cmd_fund(args.fund_name)
            elif args.command == 'concentration':
                self.cmd_concentration(args.ticker)
        except KeyboardInterrupt:
            print("\n⚠️  Operation cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    cli = InstitutionalHoldingsCLI()
    cli.run()

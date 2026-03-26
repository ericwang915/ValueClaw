#!/usr/bin/env python3
"""
Insider Trading Tracker
Analyzes insider trading activity using SEC EDGAR API and OpenInsider data.
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup


class InsiderTracker:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ValueClaw/1.0 (insider-tracker; educational use)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get_sec_edgar_data(self, ticker, start_date, end_date):
        """Fetch insider trading data from SEC EDGAR API"""
        try:
            url = f'https://efts.sec.gov/LATEST/search-index'
            params = {
                'q': f'"{ticker}"',
                'dateRange': 'custom',
                'startdt': start_date.strftime('%Y-%m-%d'),
                'enddt': end_date.strftime('%Y-%m-%d'),
                'forms': '4',
                'page': '1',
                'from': '0'
            }
            
            time.sleep(0.5)  # Rate limiting
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Warning: Could not fetch SEC EDGAR data: {e}")
            return {'hits': {'hits': []}}
    
    def get_openinsider_data(self, ticker):
        """Scrape insider trading data from OpenInsider"""
        try:
            url = f'http://openinsider.com/screener'
            params = {'s': ticker}
            
            time.sleep(1)  # Rate limiting
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the table with insider data
            table = soup.find('table', class_='tinytable')
            if not table:
                return []
            
            trades = []
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows[:20]:  # Limit to recent 20 trades
                cells = row.find_all('td')
                if len(cells) >= 8:
                    try:
                        # Extract key data from OpenInsider format
                        filing_date = cells[1].text.strip()
                        insider_name = cells[3].text.strip()
                        title = cells[4].text.strip()
                        trade_type = cells[5].text.strip()
                        shares_text = cells[6].text.strip()
                        price_text = cells[7].text.strip()
                        
                        # Parse shares and price
                        shares = self.parse_number(shares_text)
                        price = self.parse_number(price_text)
                        value = shares * price if shares and price else 0
                        
                        trades.append({
                            'filing_date': filing_date,
                            'insider_name': insider_name,
                            'title': title,
                            'trade_type': trade_type,
                            'shares': shares,
                            'price': price,
                            'value': value
                        })
                    except Exception as e:
                        continue
            
            return trades
            
        except Exception as e:
            print(f"Warning: Could not fetch OpenInsider data: {e}")
            return []
    
    def parse_number(self, text):
        """Parse number from text, handling K/M suffixes"""
        if not text or text == '-':
            return 0
        
        # Remove currency symbols and commas
        clean_text = re.sub(r'[$,]', '', text.strip())
        
        # Handle K/M suffixes
        multiplier = 1
        if clean_text.endswith('K'):
            multiplier = 1000
            clean_text = clean_text[:-1]
        elif clean_text.endswith('M'):
            multiplier = 1000000
            clean_text = clean_text[:-1]
        
        try:
            return float(clean_text) * multiplier
        except ValueError:
            return 0
    
    def analyze_trades(self, trades, min_value=0, cluster_days=30):
        """Analyze insider trades for patterns"""
        if not trades:
            return {
                'total_trades': 0,
                'buy_trades': 0,
                'sell_trades': 0,
                'net_sentiment': 0,
                'total_value': 0,
                'cluster_periods': [],
                'large_trades': []
            }
        
        buy_trades = []
        sell_trades = []
        large_trades = []
        
        for trade in trades:
            # Filter by minimum value
            if trade['value'] < min_value:
                continue
            
            # Categorize as buy or sell
            trade_type = trade.get('trade_type', '').lower()
            if 'buy' in trade_type or 'purchase' in trade_type or trade_type in ['p', 'a']:
                buy_trades.append(trade)
            elif 'sell' in trade_type or 'sale' in trade_type or trade_type in ['s', 'd']:
                sell_trades.append(trade)
            
            # Track large trades
            if trade['value'] >= 100000:  # $100K+
                large_trades.append(trade)
        
        # Calculate sentiment
        total_trades = len(buy_trades) + len(sell_trades)
        buy_ratio = len(buy_trades) / total_trades if total_trades > 0 else 0
        
        # Detect cluster buying
        cluster_periods = self.detect_clusters(buy_trades, cluster_days)
        
        return {
            'total_trades': total_trades,
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'buy_ratio': buy_ratio,
            'net_sentiment': 'Bullish' if buy_ratio > 0.6 else 'Bearish' if buy_ratio < 0.4 else 'Neutral',
            'total_value': sum(trade['value'] for trade in trades),
            'cluster_periods': cluster_periods,
            'large_trades': sorted(large_trades, key=lambda x: x['value'], reverse=True)[:10]
        }
    
    def detect_clusters(self, buy_trades, days=30):
        """Detect periods with multiple insider purchases"""
        if len(buy_trades) < 2:
            return []
        
        clusters = []
        current_cluster = []
        
        # Sort by date
        sorted_trades = sorted(buy_trades, key=lambda x: x['filing_date'])
        
        for trade in sorted_trades:
            try:
                trade_date = datetime.strptime(trade['filing_date'], '%Y-%m-%d')
            except:
                continue
            
            if not current_cluster:
                current_cluster = [trade]
            else:
                last_date = datetime.strptime(current_cluster[-1]['filing_date'], '%Y-%m-%d')
                if (trade_date - last_date).days <= days:
                    current_cluster.append(trade)
                else:
                    if len(current_cluster) >= 2:
                        clusters.append(current_cluster)
                    current_cluster = [trade]
        
        # Check final cluster
        if len(current_cluster) >= 2:
            clusters.append(current_cluster)
        
        return clusters
    
    def format_output(self, ticker, analysis, trades, verbose=False, cluster_only=False):
        """Format analysis output for display"""
        output = []
        output.append(f"\n🎯 Insider Trading Analysis for {ticker.upper()}")
        output.append("=" * 50)
        
        if analysis['total_trades'] == 0:
            output.append("❌ No insider trading data found for the specified criteria.")
            return "\n".join(output)
        
        # Summary
        output.append(f"\n📊 TRADING SUMMARY")
        output.append(f"Total Transactions: {analysis['total_trades']}")
        output.append(f"Buy Transactions: {analysis['buy_trades']} ({analysis['buy_trades']/analysis['total_trades']*100:.1f}%)")
        output.append(f"Sell Transactions: {analysis['sell_trades']} ({analysis['sell_trades']/analysis['total_trades']*100:.1f}%)")
        output.append(f"Net Sentiment: {analysis['net_sentiment']} {'📈' if analysis['net_sentiment'] == 'Bullish' else '📉' if analysis['net_sentiment'] == 'Bearish' else '➡️'}")
        output.append(f"Total Transaction Value: ${analysis['total_value']:,.0f}")
        
        # Cluster analysis
        if analysis['cluster_periods']:
            output.append(f"\n🔥 CLUSTER BUYING DETECTED ({len(analysis['cluster_periods'])} periods)")
            for i, cluster in enumerate(analysis['cluster_periods'], 1):
                total_value = sum(trade['value'] for trade in cluster)
                insiders = len(set(trade['insider_name'] for trade in cluster))
                output.append(f"  Cluster {i}: {len(cluster)} buys by {insiders} insiders (${total_value:,.0f})")
        elif not cluster_only:
            output.append(f"\n📊 No cluster buying detected in recent period")
        
        # Large trades
        if analysis['large_trades'] and not cluster_only:
            output.append(f"\n💰 SIGNIFICANT TRADES (>${min_value:,.0f}+)")
            for trade in analysis['large_trades'][:5]:
                trade_type_emoji = "🟢" if 'buy' in trade.get('trade_type', '').lower() else "🔴"
                output.append(f"  {trade_type_emoji} {trade['filing_date']} | {trade['insider_name'][:30]} | "
                          f"{trade['trade_type']} | ${trade['value']:,.0f}")
        
        if verbose and not cluster_only:
            output.append(f"\n📋 RECENT TRANSACTIONS")
            for trade in trades[:10]:
                if trade['value'] > 0:
                    trade_type_emoji = "🟢" if 'buy' in trade.get('trade_type', '').lower() else "🔴"
                    output.append(f"  {trade_type_emoji} {trade['filing_date']} | {trade['insider_name'][:25]} | "
                              f"{trade['title'][:20]} | {trade['trade_type']} | "
                              f"{trade['shares']:,.0f} shares @ ${trade['price']:.2f} = ${trade['value']:,.0f}")
        
        # Only show clusters if cluster_only flag is set
        if cluster_only and not analysis['cluster_periods']:
            output = [f"\n🎯 Insider Trading Analysis for {ticker.upper()}",
                     "=" * 50,
                     "❌ No cluster buying detected in the specified period."]
        
        return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description='Track insider trading activity for stocks')
    parser.add_argument('ticker', help='Stock ticker symbol')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)', 
                       default=(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'))
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)', 
                       default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument('--days', type=int, help='Look back N days from today')
    parser.add_argument('--min-value', type=float, default=0, 
                       help='Minimum transaction value to include')
    parser.add_argument('--cluster-only', action='store_true', 
                       help='Only show cluster buying periods')
    parser.add_argument('--verbose', action='store_true', 
                       help='Show detailed transaction list')
    
    args = parser.parse_args()
    
    # Handle days parameter
    if args.days:
        args.end_date = datetime.now().strftime('%Y-%m-%d')
        args.start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError:
        print("Error: Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)
    
    if start_date > end_date:
        print("Error: Start date must be before end date")
        sys.exit(1)
    
    # Initialize tracker and fetch data
    tracker = InsiderTracker()
    
    print(f"🔍 Fetching insider trading data for {args.ticker.upper()}...")
    
    # Fetch data from both sources
    sec_data = tracker.get_sec_edgar_data(args.ticker, start_date, end_date)
    openinsider_data = tracker.get_openinsider_data(args.ticker)
    
    # Use OpenInsider data as primary source (more reliable parsing)
    trades = openinsider_data
    
    # Analyze the data
    analysis = tracker.analyze_trades(trades, args.min_value)
    
    # Format and display results
    output = tracker.format_output(args.ticker, analysis, trades, 
                                 args.verbose, args.cluster_only)
    print(output)


if __name__ == "__main__":
    main()
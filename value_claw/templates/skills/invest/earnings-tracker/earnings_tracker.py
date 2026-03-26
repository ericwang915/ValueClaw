#!/usr/bin/env python3
"""
Earnings Tracker
Track earnings releases and analyze historical earnings performance.
"""

import argparse
import sys
from datetime import datetime, timedelta

import yfinance as yf


class EarningsTracker:
    def __init__(self):
        # Major companies for calendar filtering
        self.major_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX',
            'AMD', 'INTC', 'CRM', 'ORCL', 'ADBE', 'NOW', 'UBER', 'ABNB',
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'KO', 'PEP', 'WMT', 'TGT',
            'DIS', 'PYPL', 'SQ', 'SHOP', 'ZM', 'SNOW', 'PLTR', 'DDOG'
        ]
    
    def get_earnings_calendar(self, start_date, end_date, major_only=False):
        """Get earnings calendar for date range"""
        calendar = []
        
        # Define tickers to check
        tickers_to_check = self.major_tickers if major_only else self.major_tickers  # Could be expanded
        
        print(f"📊 Checking earnings for {len(tickers_to_check)} companies...")
        
        for ticker in tickers_to_check:
            try:
                stock = yf.Ticker(ticker)
                
                # Get earnings dates
                earnings_dates = stock.earnings_dates
                if earnings_dates is not None and not earnings_dates.empty:
                    # Filter by date range
                    mask = (earnings_dates.index >= start_date) & (earnings_dates.index <= end_date)
                    upcoming = earnings_dates[mask]
                    
                    for date, row in upcoming.iterrows():
                        earnings_estimate = row.get('EPS Estimate', None)
                        reported_eps = row.get('Reported EPS', None)
                        
                        calendar.append({
                            'ticker': ticker,
                            'date': date,
                            'eps_estimate': earnings_estimate,
                            'reported_eps': reported_eps,
                            'timing': self.get_earnings_timing(date)
                        })
                
                # Small delay to avoid rate limiting
                import time
                time.sleep(0.1)
                
            except Exception as e:
                continue  # Skip tickers that fail
        
        return sorted(calendar, key=lambda x: x['date'])
    
    def get_earnings_timing(self, date):
        """Determine if earnings are pre-market or post-market"""
        # This is a simplified approach - in reality, timing varies
        # Most companies report after market close
        return "After Market Close"
    
    def analyze_earnings_history(self, ticker):
        """Analyze historical earnings performance"""
        try:
            stock = yf.Ticker(ticker)
            
            # Get earnings history
            earnings = stock.earnings_dates
            if earnings is None or earnings.empty:
                return None
            
            # Get stock price history for drift analysis
            hist = stock.history(period="2y")
            
            analysis = {
                'ticker': ticker,
                'earnings_data': [],
                'surprise_stats': {},
                'drift_stats': {}
            }
            
            # Process each earnings release
            for date, row in earnings.head(8).iterrows():  # Last 8 quarters
                eps_estimate = row.get('EPS Estimate')
                reported_eps = row.get('Reported EPS')
                
                earnings_record = {
                    'date': date,
                    'eps_estimate': eps_estimate,
                    'reported_eps': reported_eps,
                    'surprise': None,
                    'surprise_pct': None
                }
                
                # Calculate surprise
                if eps_estimate is not None and reported_eps is not None:
                    surprise = reported_eps - eps_estimate
                    surprise_pct = (surprise / abs(eps_estimate)) * 100 if eps_estimate != 0 else None
                    
                    earnings_record['surprise'] = surprise
                    earnings_record['surprise_pct'] = surprise_pct
                
                # Calculate price drift
                drift_data = self.calculate_price_drift(hist, date)
                earnings_record['price_drift'] = drift_data
                
                analysis['earnings_data'].append(earnings_record)
            
            # Calculate aggregate statistics
            analysis['surprise_stats'] = self.calculate_surprise_stats(analysis['earnings_data'])
            analysis['drift_stats'] = self.calculate_drift_stats(analysis['earnings_data'])
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing earnings history for {ticker}: {e}")
            return None
    
    def calculate_price_drift(self, price_history, earnings_date):
        """Calculate price performance after earnings"""
        try:
            # Find the closest trading date to earnings date
            earnings_date_ts = earnings_date.tz_localize(None) if earnings_date.tz is not None else earnings_date
            
            # Get price on earnings date (or closest business day after)
            base_date = None
            base_price = None
            
            for i in range(5):  # Look up to 5 days ahead for trading day
                check_date = earnings_date_ts + timedelta(days=i)
                if check_date in price_history.index:
                    base_date = check_date
                    base_price = price_history.loc[check_date]['Close']
                    break
            
            if base_price is None:
                return None
            
            # Calculate performance at various intervals
            drift = {}
            for days in [1, 5, 20]:
                target_date = base_date + timedelta(days=days)
                
                # Find next available trading day
                found_price = None
                for i in range(5):  # Look up to 5 days ahead
                    check_date = target_date + timedelta(days=i)
                    if check_date in price_history.index:
                        found_price = price_history.loc[check_date]['Close']
                        break
                
                if found_price:
                    performance = ((found_price - base_price) / base_price) * 100
                    drift[f'day_{days}'] = performance
            
            return drift
            
        except Exception:
            return None
    
    def calculate_surprise_stats(self, earnings_data):
        """Calculate earnings surprise statistics"""
        surprises = [e['surprise'] for e in earnings_data if e['surprise'] is not None]
        surprise_pcts = [e['surprise_pct'] for e in earnings_data if e['surprise_pct'] is not None]
        
        if not surprises:
            return {}
        
        beats = len([s for s in surprises if s > 0])
        misses = len([s for s in surprises if s < 0])
        meets = len([s for s in surprises if s == 0])
        total = len(surprises)
        
        return {
            'total_quarters': total,
            'beats': beats,
            'misses': misses,
            'meets': meets,
            'beat_rate': (beats / total) * 100 if total > 0 else 0,
            'avg_surprise': sum(surprises) / len(surprises),
            'avg_surprise_pct': sum(surprise_pcts) / len(surprise_pcts) if surprise_pcts else 0
        }
    
    def calculate_drift_stats(self, earnings_data):
        """Calculate post-earnings drift statistics"""
        drift_1d = [e['price_drift']['day_1'] for e in earnings_data 
                   if e['price_drift'] and 'day_1' in e['price_drift']]
        drift_5d = [e['price_drift']['day_5'] for e in earnings_data 
                   if e['price_drift'] and 'day_5' in e['price_drift']]
        drift_20d = [e['price_drift']['day_20'] for e in earnings_data 
                    if e['price_drift'] and 'day_20' in e['price_drift']]
        
        stats = {}
        
        for period, data in [('1d', drift_1d), ('5d', drift_5d), ('20d', drift_20d)]:
            if data:
                stats[period] = {
                    'avg_return': sum(data) / len(data),
                    'positive_count': len([d for d in data if d > 0]),
                    'negative_count': len([d for d in data if d < 0]),
                    'success_rate': (len([d for d in data if d > 0]) / len(data)) * 100
                }
        
        return stats
    
    def get_next_earnings(self, ticker):
        """Get next earnings date for ticker"""
        try:
            stock = yf.Ticker(ticker)
            earnings_dates = stock.earnings_dates
            
            if earnings_dates is None or earnings_dates.empty:
                return None
            
            # Find next upcoming earnings
            today = datetime.now()
            upcoming = earnings_dates[earnings_dates.index >= today]
            
            if upcoming.empty:
                return None
            
            next_earnings = upcoming.iloc[0]
            return {
                'date': upcoming.index[0],
                'eps_estimate': next_earnings.get('EPS Estimate'),
                'timing': self.get_earnings_timing(upcoming.index[0])
            }
            
        except Exception:
            return None
    
    def format_calendar_output(self, calendar):
        """Format earnings calendar output"""
        if not calendar:
            return "❌ No earnings found for the specified period."
        
        output = []
        output.append("📊 EARNINGS CALENDAR")
        output.append("=" * 50)
        
        # Group by date
        calendar_by_date = {}
        for event in calendar:
            date_str = event['date'].strftime('%Y-%m-%d')
            day_name = event['date'].strftime('%A')
            
            if date_str not in calendar_by_date:
                calendar_by_date[date_str] = {'day': day_name, 'events': []}
            
            calendar_by_date[date_str]['events'].append(event)
        
        # Sort and display
        for date_str in sorted(calendar_by_date.keys()):
            day_data = calendar_by_date[date_str]
            
            output.append(f"\n📅 {day_data['day']}, {date_str}")
            output.append("-" * 30)
            
            for event in day_data['events']:
                eps_str = f"EPS Est: ${event['eps_estimate']:.2f}" if event['eps_estimate'] else "EPS Est: N/A"
                timing_emoji = "🌅" if "Pre" in event['timing'] else "🌆"
                
                output.append(f"  {timing_emoji} {event['ticker']} | {eps_str} | {event['timing']}")
        
        output.append(f"\nTotal Companies: {len(calendar)}")
        
        return "\n".join(output)
    
    def format_analysis_output(self, analysis, show_details=True):
        """Format earnings analysis output"""
        if not analysis:
            return "❌ No earnings data available for analysis."
        
        output = []
        output.append(f"📊 EARNINGS ANALYSIS - {analysis['ticker']}")
        output.append("=" * 50)
        
        # Next earnings
        next_earnings = self.get_next_earnings(analysis['ticker'])
        if next_earnings:
            output.append(f"\n📅 NEXT EARNINGS")
            output.append(f"Date: {next_earnings['date'].strftime('%Y-%m-%d')}")
            if next_earnings['eps_estimate']:
                output.append(f"EPS Estimate: ${next_earnings['eps_estimate']:.2f}")
            output.append(f"Timing: {next_earnings['timing']}")
        
        # Surprise statistics
        surprise_stats = analysis['surprise_stats']
        if surprise_stats:
            beat_emoji = "🎯" if surprise_stats['beat_rate'] >= 75 else "📈" if surprise_stats['beat_rate'] >= 50 else "📉"
            output.append(f"\n{beat_emoji} EARNINGS SURPRISE HISTORY (Last {surprise_stats['total_quarters']} Quarters)")
            output.append(f"Beat Rate: {surprise_stats['beat_rate']:.1f}% ({surprise_stats['beats']}/{surprise_stats['total_quarters']})")
            output.append(f"Avg Surprise: ${surprise_stats['avg_surprise']:.3f} ({surprise_stats['avg_surprise_pct']:+.1f}%)")
            output.append(f"Beats: {surprise_stats['beats']} | Misses: {surprise_stats['misses']} | Meets: {surprise_stats['meets']}")
        
        # Post-earnings drift
        drift_stats = analysis['drift_stats']
        if drift_stats:
            output.append(f"\n📈 POST-EARNINGS PRICE DRIFT")
            
            for period in ['1d', '5d', '20d']:
                if period in drift_stats:
                    stats = drift_stats[period]
                    period_emoji = "⚡" if period == '1d' else "📊" if period == '5d' else "📈"
                    output.append(f"  {period_emoji} {period.upper()}: {stats['avg_return']:+.1f}% avg "
                               f"({stats['success_rate']:.0f}% positive)")
        
        # Recent earnings details
        if show_details and analysis['earnings_data']:
            output.append(f"\n📋 RECENT EARNINGS HISTORY")
            output.append(f"{'Date':<12} {'Est':<8} {'Act':<8} {'Surprise':<10} {'1D%':<8} {'5D%':<8}")
            output.append("-" * 60)
            
            for earnings in analysis['earnings_data'][:5]:  # Show last 5
                date_str = earnings['date'].strftime('%Y-%m-%d')
                est_str = f"${earnings['eps_estimate']:.2f}" if earnings['eps_estimate'] else "N/A"
                act_str = f"${earnings['reported_eps']:.2f}" if earnings['reported_eps'] else "N/A"
                
                if earnings['surprise_pct']:
                    surprise_str = f"{earnings['surprise_pct']:+.1f}%"
                    surprise_emoji = "✅" if earnings['surprise'] > 0 else "❌" if earnings['surprise'] < 0 else "➡️"
                else:
                    surprise_str = "N/A"
                    surprise_emoji = ""
                
                drift = earnings['price_drift'] or {}
                drift_1d = f"{drift.get('day_1', 0):+.1f}%" if drift.get('day_1') else "N/A"
                drift_5d = f"{drift.get('day_5', 0):+.1f}%" if drift.get('day_5') else "N/A"
                
                output.append(f"{surprise_emoji}{date_str:<11} {est_str:<8} {act_str:<8} "
                           f"{surprise_str:<10} {drift_1d:<8} {drift_5d:<8}")
        
        return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description='Track earnings releases and analyze performance')
    parser.add_argument('ticker', nargs='?', help='Stock ticker for individual analysis')
    parser.add_argument('--calendar', action='store_true', help='Show earnings calendar')
    parser.add_argument('--next-week', action='store_true', help='Show next week (with --calendar)')
    parser.add_argument('--major-only', action='store_true', help='Major companies only')
    parser.add_argument('--surprise-history', action='store_true', help='Focus on surprise history')
    parser.add_argument('--drift-analysis', action='store_true', help='Focus on price drift')
    parser.add_argument('--estimates', action='store_true', help='Show EPS estimates')
    parser.add_argument('--beat-rate', action='store_true', help='Calculate beat rate')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.ticker and not args.calendar:
        print("Error: Specify either a ticker symbol or use --calendar")
        sys.exit(1)
    
    tracker = EarningsTracker()
    
    if args.calendar:
        # Show earnings calendar
        if args.next_week:
            start_date = datetime.now() + timedelta(days=7)
            end_date = start_date + timedelta(days=7)
        else:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=7)
        
        print(f"📊 Fetching earnings calendar...")
        calendar = tracker.get_earnings_calendar(start_date, end_date, args.major_only)
        output = tracker.format_calendar_output(calendar)
        print(output)
        
    else:
        # Analyze individual ticker
        print(f"📊 Analyzing earnings history for {args.ticker.upper()}...")
        analysis = tracker.analyze_earnings_history(args.ticker)
        
        if not analysis:
            print(f"❌ No earnings data found for {args.ticker}")
            sys.exit(1)
        
        # Show specific analysis based on flags
        show_details = not (args.surprise_history or args.drift_analysis or args.estimates)
        output = tracker.format_analysis_output(analysis, show_details)
        print(output)


if __name__ == "__main__":
    main()
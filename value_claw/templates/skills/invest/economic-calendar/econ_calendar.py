#!/usr/bin/env python3
"""
Economic Calendar CLI Tool

Fetches upcoming economic events from Forex Factory API and other sources.
Supports filtering by country, impact level, and date ranges.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests


class EconomicCalendar:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Country code mappings
        self.country_mappings = {
            'US': ['USD', 'USA', 'United States'],
            'CN': ['CNY', 'CHN', 'China'],
            'EU': ['EUR', 'European Union', 'Germany', 'France', 'Italy'],
            'JP': ['JPY', 'JPN', 'Japan'],
        }

        # Impact level mappings
        self.impact_mappings = {
            'high': ['High', 'high', '3'],
            'medium': ['Medium', 'medium', '2'],
            'low': ['Low', 'low', '1']
        }

    def fetch_forex_factory_data(self) -> List[Dict[str, Any]]:
        """Fetch data from Forex Factory API."""
        url = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json'

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data if isinstance(data, list) else []

        except requests.RequestException as e:
            print(f"Error fetching Forex Factory data: {e}", file=sys.stderr)
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from Forex Factory: {e}", file=sys.stderr)
            return []

    def fetch_investing_com_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Fallback: attempt to fetch from investing.com (simplified)."""
        # Note: This is a simplified implementation since investing.com requires more complex scraping
        # In a real implementation, you'd need to handle CSRF tokens, cookies, etc.

        url = 'https://www.investing.com/economic-calendar/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        try:
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # For this implementation, return empty list as investing.com scraping
            # would require more complex parsing and handling of dynamic content
            print("Note: Investing.com scraping not fully implemented. Using Forex Factory data.", file=sys.stderr)
            return []

        except requests.RequestException as e:
            print(f"Error fetching from investing.com: {e}", file=sys.stderr)
            return []

    def normalize_event_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize event data from various sources to a common format."""
        normalized_events = []

        for event in raw_data:
            try:
                # Handle Forex Factory format
                normalized_event = {
                    'date': self._parse_date(event.get('date', '')),
                    'time': self._parse_time(event.get('time', '')),
                    'country': self._normalize_country(event.get('country', event.get('currency', ''))),
                    'event': event.get('title', event.get('event', 'Unknown Event')),
                    'impact': self._normalize_impact(event.get('impact', '')),
                    'previous': event.get('previous', ''),
                    'forecast': event.get('forecast', ''),
                    'actual': event.get('actual', '')
                }

                if normalized_event['date']:  # Only add events with valid dates
                    normalized_events.append(normalized_event)

            except Exception as e:
                print(f"Error normalizing event: {e}", file=sys.stderr)
                continue

        return normalized_events

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse and normalize date string."""
        if not date_str:
            return None

        try:
            # Handle various date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y%m%d']:
                try:
                    dt = datetime.strptime(str(date_str), fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue

            # If it's a timestamp
            if isinstance(date_str, (int, float)) or date_str.isdigit():
                dt = datetime.fromtimestamp(int(date_str))
                return dt.strftime('%Y-%m-%d')

            return None

        except Exception:
            return None

    def _parse_time(self, time_str: str) -> str:
        """Parse and normalize time string."""
        if not time_str or time_str.lower() in ['all day', 'tentative']:
            return 'All Day'

        try:
            # Handle various time formats
            for fmt in ['%H:%M', '%I:%M %p', '%H%M']:
                try:
                    dt = datetime.strptime(str(time_str), fmt)
                    return dt.strftime('%H:%M')
                except ValueError:
                    continue

            return str(time_str)

        except Exception:
            return str(time_str)

    def _normalize_country(self, country_str: str) -> str:
        """Normalize country/currency codes."""
        if not country_str:
            return 'Unknown'

        country_upper = str(country_str).upper()

        # Direct mapping
        for code, variants in self.country_mappings.items():
            if country_upper in [v.upper() for v in variants]:
                return code

        # Return original if no mapping found
        return str(country_str)

    def _normalize_impact(self, impact_str: str) -> str:
        """Normalize impact levels."""
        if not impact_str:
            return 'Low'

        impact_str = str(impact_str).strip()

        for level, variants in self.impact_mappings.items():
            if impact_str in variants:
                return level.capitalize()

        # Default mapping based on common patterns
        if impact_str.lower() in ['high', 'red', '3']:
            return 'High'
        elif impact_str.lower() in ['medium', 'orange', 'yellow', '2']:
            return 'Medium'
        else:
            return 'Low'

    def filter_events(self, events: List[Dict[str, Any]], country_filter: str,
                     impact_filter: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Filter events based on criteria."""
        filtered = []

        for event in events:
            # Date filter
            if start_date and end_date:
                event_date = event.get('date')
                if not event_date or not (start_date <= event_date <= end_date):
                    continue

            # Country filter
            if country_filter != 'all':
                event_country = event.get('country', '').upper()
                if country_filter.upper() != event_country:
                    continue

            # Impact filter
            if impact_filter != 'all':
                event_impact = event.get('impact', '').lower()
                if impact_filter.lower() != event_impact:
                    continue

            filtered.append(event)

        return filtered

    def format_table_output(self, events: List[Dict[str, Any]]) -> str:
        """Format events as a table."""
        if not events:
            return "No economic events found matching the criteria."

        # Sort by date and time
        events.sort(key=lambda x: (x.get('date', ''), x.get('time', '')))

        # Calculate column widths
        widths = {
            'date': max(10, max(len(str(e.get('date', ''))) for e in events)),
            'time': max(8, max(len(str(e.get('time', ''))) for e in events)),
            'country': max(7, max(len(str(e.get('country', ''))) for e in events)),
            'event': max(30, min(50, max(len(str(e.get('event', ''))) for e in events))),
            'impact': 6,
            'previous': 8,
            'forecast': 8,
            'actual': 8
        }

        # Header
        header = (f"{'Date':<{widths['date']}} "
                 f"{'Time':<{widths['time']}} "
                 f"{'Country':<{widths['country']}} "
                 f"{'Event':<{widths['event']}} "
                 f"{'Impact':<{widths['impact']}} "
                 f"{'Previous':<{widths['previous']}} "
                 f"{'Forecast':<{widths['forecast']}} "
                 f"{'Actual':<{widths['actual']}}")

        separator = '-' * len(header)

        lines = [header, separator]

        for event in events:
            # Truncate long event names
            event_name = str(event.get('event', ''))
            if len(event_name) > widths['event']:
                event_name = event_name[:widths['event']-3] + '...'

            # Add warning emoji for high impact events
            impact = str(event.get('impact', 'Low'))
            if impact.lower() == 'high':
                impact = f"⚠️ {impact}"

            line = (f"{str(event.get('date', '')):<{widths['date']}} "
                   f"{str(event.get('time', '')):<{widths['time']}} "
                   f"{str(event.get('country', '')):<{widths['country']}} "
                   f"{event_name:<{widths['event']}} "
                   f"{impact:<{widths['impact']}} "
                   f"{str(event.get('previous', '')):<{widths['previous']}} "
                   f"{str(event.get('forecast', '')):<{widths['forecast']}} "
                   f"{str(event.get('actual', '')):<{widths['actual']}}")

            lines.append(line)

        return '\n'.join(lines)

    def get_date_range(self, command: str, start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> tuple[str, str]:
        """Get start and end dates based on command."""
        today = datetime.now()

        if command == 'week':
            # Current week (Monday to Sunday)
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)
            return monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')

        elif command == 'next':
            # Next week (Monday to Sunday)
            next_monday = today + timedelta(days=(7 - today.weekday()))
            next_sunday = next_monday + timedelta(days=6)
            return next_monday.strftime('%Y-%m-%d'), next_sunday.strftime('%Y-%m-%d')

        elif command == 'date' and start_date and end_date:
            return start_date, end_date

        else:
            # Default to this week
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)
            return monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')


def main():
    parser = argparse.ArgumentParser(
        description='Economic Calendar CLI - Fetch upcoming economic events',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s week --country US --impact high
  %(prog)s next --country EU
  %(prog)s date --start 2024-01-15 --end 2024-01-20 --impact medium
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Week command
    week_parser = subparsers.add_parser('week', help='Show events for this week')
    week_parser.add_argument('--country', choices=['US', 'CN', 'EU', 'JP', 'all'],
                           default='all', help='Filter by country (default: all)')
    week_parser.add_argument('--impact', choices=['high', 'medium', 'low', 'all'],
                           default='all', help='Filter by impact level (default: all)')

    # Next command
    next_parser = subparsers.add_parser('next', help='Show events for next week')
    next_parser.add_argument('--country', choices=['US', 'CN', 'EU', 'JP', 'all'],
                           default='all', help='Filter by country (default: all)')
    next_parser.add_argument('--impact', choices=['high', 'medium', 'low', 'all'],
                           default='all', help='Filter by impact level (default: all)')

    # Date command
    date_parser = subparsers.add_parser('date', help='Show events for custom date range')
    date_parser.add_argument('--start', required=True,
                           help='Start date (YYYY-MM-DD)')
    date_parser.add_argument('--end', required=True,
                           help='End date (YYYY-MM-DD)')
    date_parser.add_argument('--country', choices=['US', 'CN', 'EU', 'JP', 'all'],
                           default='all', help='Filter by country (default: all)')
    date_parser.add_argument('--impact', choices=['high', 'medium', 'low', 'all'],
                           default='all', help='Filter by impact level (default: all)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Validate date format for date command
    if args.command == 'date':
        try:
            datetime.strptime(args.start, '%Y-%m-%d')
            datetime.strptime(args.end, '%Y-%m-%d')
        except ValueError:
            print("Error: Date format must be YYYY-MM-DD", file=sys.stderr)
            return 1

    # Initialize calendar
    calendar = EconomicCalendar()

    # Get date range
    if args.command == 'date':
        start_date, end_date = calendar.get_date_range(args.command, args.start, args.end)
    else:
        start_date, end_date = calendar.get_date_range(args.command)

    # Fetch data
    print(f"Fetching economic events from {start_date} to {end_date}...", file=sys.stderr)

    # Try Forex Factory first
    raw_events = calendar.fetch_forex_factory_data()

    # If Forex Factory fails or returns no data, try investing.com (fallback)
    if not raw_events:
        print("Forex Factory returned no data, trying alternative sources...", file=sys.stderr)
        raw_events = calendar.fetch_investing_com_data(start_date, end_date)

    if not raw_events:
        print("No data available from any source.", file=sys.stderr)
        return 1

    # Normalize and filter events
    events = calendar.normalize_event_data(raw_events)
    filtered_events = calendar.filter_events(events, args.country, args.impact,
                                           start_date, end_date)

    # Output results
    output = calendar.format_table_output(filtered_events)
    print(output)

    # Summary
    print(f"\nFound {len(filtered_events)} events", file=sys.stderr)
    if args.country != 'all':
        print(f"Filtered by country: {args.country}", file=sys.stderr)
    if args.impact != 'all':
        print(f"Filtered by impact: {args.impact}", file=sys.stderr)

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

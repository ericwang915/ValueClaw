---
name: market-sentiment
description: "Analyze overall market sentiment using multiple indicators including CNN Fear & Greed Index, VIX levels, Put/Call ratios, and market breadth metrics. Provides composite sentiment score."
dependencies: requests,beautifulsoup4,yfinance
metadata:
  emoji: "🎭"
---

# Market Sentiment Analyzer

Analyze overall market sentiment using multiple technical and behavioral indicators. This skill combines various sentiment metrics to provide a comprehensive view of market psychology and potential turning points.

## Usage

The market sentiment analyzer provides a dashboard of key sentiment indicators with interpretation and composite scoring.

```bash
# Get current market sentiment dashboard
python3 sentiment.py

# Include historical comparison
python3 sentiment.py --historical

# Focus on specific sentiment categories
python3 sentiment.py --category fear-greed
python3 sentiment.py --category volatility
python3 sentiment.py --category breadth

# Export data in JSON format
python3 sentiment.py --output json
```

## Commands

- **Dashboard**: `python3 sentiment.py` - Complete sentiment overview with all indicators
- **Historical**: `--historical` - Include 20-day averages and historical context
- **Category Filter**: `--category CATEGORY` - Focus on specific indicator group
  - `fear-greed`: CNN Fear & Greed Index
  - `volatility`: VIX and volatility metrics  
  - `breadth`: Market breadth and participation metrics
  - `options`: Put/Call ratios and options sentiment
- **Output Format**: `--output FORMAT` - Choose output format (text, json)
- **Quick Mode**: `--quick` - Faster execution with cached data where possible

## Indicators Tracked

**Fear & Greed Index**: CNN's composite sentiment indicator (0-100 scale)
**VIX Level**: Current volatility index vs 20-day average
**Put/Call Ratio**: Options sentiment from equity options activity
**Market Breadth**: Percentage of S&P 500 stocks above 200-day moving average
**Composite Score**: Weighted average of all indicators with interpretation

The tool provides emoji-based visual indicators and actionable insights for different market conditions.
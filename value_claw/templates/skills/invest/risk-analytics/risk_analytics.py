#!/usr/bin/env python3
"""
Risk Analytics
Comprehensive risk analysis for portfolios and individual securities.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta

import numpy as np
import yfinance as yf


class RiskAnalytics:
    def __init__(self):
        self.risk_free_rate = 0.03  # 3% annual risk-free rate
        
        # Historical stress test periods
        self.stress_scenarios = {
            'covid': ('2020-02-19', '2020-03-23'),  # COVID crash
            'dotcom': ('2000-03-10', '2002-10-09'),  # Dot-com crash
            'gfc': ('2007-10-09', '2009-03-09'),     # Great Financial Crisis
            'black_monday': ('1987-08-25', '1987-12-04'),  # 1987 crash
            'volmageddon': ('2018-01-26', '2018-02-09'),   # VIX spike
        }
    
    def get_price_data(self, tickers, period='2y'):
        """Get price data for analysis"""
        try:
            if isinstance(tickers, str):
                tickers = [tickers]
            
            # Download data
            data = yf.download(tickers, period=period, progress=False)
            
            if data.empty:
                return None, None
            
            # Handle single vs multiple tickers
            if len(tickers) == 1:
                prices = data['Adj Close'].dropna()
                returns = prices.pct_change().dropna()
            else:
                prices = data['Adj Close'].dropna()
                returns = prices.pct_change().dropna()
            
            return prices, returns
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None, None
    
    def calculate_var(self, returns, confidence=95, time_horizon=1):
        """Calculate Value at Risk using historical simulation"""
        if returns.empty:
            return None
        
        # Convert to numpy array for single series
        if hasattr(returns, 'values'):
            returns_array = returns.values
        else:
            returns_array = np.array(returns)
        
        # Remove NaN values
        returns_clean = returns_array[~np.isnan(returns_array)]
        
        if len(returns_clean) == 0:
            return None
        
        # Calculate percentiles for VaR
        alpha = (100 - confidence) / 100
        var_1d = np.percentile(returns_clean, alpha * 100)
        
        # Scale for different time horizons
        var_scaled = var_1d * np.sqrt(time_horizon)
        
        # Calculate Conditional VaR (Expected Shortfall)
        mask = returns_clean <= var_1d
        if np.any(mask):
            cvar_1d = returns_clean[mask].mean()
            cvar_scaled = cvar_1d * np.sqrt(time_horizon)
        else:
            cvar_scaled = var_scaled
        
        return {
            'var_1d': var_1d * 100,  # Convert to percentage
            'var_scaled': var_scaled * 100,
            'cvar_1d': cvar_1d * 100 if 'cvar_1d' in locals() else var_scaled * 100,
            'cvar_scaled': cvar_scaled * 100,
            'confidence': confidence,
            'time_horizon': time_horizon
        }
    
    def calculate_sharpe_ratio(self, returns, risk_free_rate=None):
        """Calculate Sharpe ratio"""
        if returns.empty:
            return None
        
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate
        
        # Annualize returns and volatility
        annual_return = returns.mean() * 252
        annual_vol = returns.std() * np.sqrt(252)
        
        if annual_vol == 0:
            return 0
        
        sharpe = (annual_return - risk_free_rate) / annual_vol
        
        return {
            'sharpe_ratio': sharpe,
            'annual_return': annual_return * 100,
            'annual_volatility': annual_vol * 100,
            'risk_free_rate': risk_free_rate * 100
        }
    
    def calculate_sortino_ratio(self, returns, risk_free_rate=None):
        """Calculate Sortino ratio (using downside deviation)"""
        if returns.empty:
            return None
        
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate
        
        annual_return = returns.mean() * 252
        
        # Downside deviation (only negative returns)
        negative_returns = returns[returns < 0]
        if len(negative_returns) == 0:
            downside_deviation = 0
        else:
            downside_deviation = negative_returns.std() * np.sqrt(252)
        
        if downside_deviation == 0:
            return float('inf') if annual_return > risk_free_rate else 0
        
        sortino = (annual_return - risk_free_rate) / downside_deviation
        
        return {
            'sortino_ratio': sortino,
            'annual_return': annual_return * 100,
            'downside_deviation': downside_deviation * 100,
            'negative_periods': len(negative_returns)
        }
    
    def calculate_maximum_drawdown(self, prices):
        """Calculate maximum drawdown and recovery periods"""
        if prices.empty:
            return None
        
        # Calculate cumulative returns
        cumulative = (1 + prices.pct_change()).cumprod()
        
        # Calculate running maximum
        peak = cumulative.expanding().max()
        
        # Calculate drawdown
        drawdown = (cumulative - peak) / peak
        
        # Find maximum drawdown
        max_dd = drawdown.min()
        max_dd_date = drawdown.idxmin()
        
        # Find peak before max drawdown
        peak_before_max_dd = peak.loc[:max_dd_date].idxmax()
        
        # Find recovery date (if any)
        recovery_mask = (cumulative.loc[max_dd_date:] >= peak.loc[max_dd_date])
        if recovery_mask.any():
            recovery_date = cumulative.loc[max_dd_date:][recovery_mask].index[0]
            recovery_days = (recovery_date - max_dd_date).days
        else:
            recovery_date = None
            recovery_days = None
        
        return {
            'max_drawdown': max_dd * 100,
            'max_dd_date': max_dd_date,
            'peak_date': peak_before_max_dd,
            'recovery_date': recovery_date,
            'recovery_days': recovery_days,
            'current_drawdown': drawdown.iloc[-1] * 100
        }
    
    def calculate_beta(self, asset_returns, benchmark_returns):
        """Calculate beta vs benchmark"""
        if asset_returns.empty or benchmark_returns.empty:
            return None
        
        # Align the series
        aligned_data = asset_returns.align(benchmark_returns, join='inner')
        asset_aligned = aligned_data[0].dropna()
        benchmark_aligned = aligned_data[1].dropna()
        
        if len(asset_aligned) < 20:  # Need sufficient data
            return None
        
        # Calculate covariance and variance
        covariance = np.cov(asset_aligned, benchmark_aligned)[0, 1]
        benchmark_variance = np.var(benchmark_aligned)
        
        if benchmark_variance == 0:
            return None
        
        beta = covariance / benchmark_variance
        
        # Calculate correlation
        correlation = np.corrcoef(asset_aligned, benchmark_aligned)[0, 1]
        
        # Calculate alpha
        asset_return = asset_aligned.mean() * 252
        benchmark_return = benchmark_aligned.mean() * 252
        alpha = asset_return - beta * benchmark_return
        
        return {
            'beta': beta,
            'alpha': alpha * 100,  # Annualized alpha in percentage
            'correlation': correlation,
            'r_squared': correlation ** 2
        }
    
    def calculate_correlation_matrix(self, returns):
        """Calculate correlation matrix for multiple assets"""
        if returns.empty:
            return None
        
        correlation_matrix = returns.corr()
        
        # Additional statistics
        avg_correlation = correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].mean()
        
        return {
            'correlation_matrix': correlation_matrix,
            'average_correlation': avg_correlation,
            'diversification_ratio': 1 - avg_correlation  # Simple diversification measure
        }
    
    def stress_test(self, prices, scenario='covid'):
        """Perform stress testing using historical scenarios"""
        if scenario not in self.stress_scenarios:
            return None
        
        start_date, end_date = self.stress_scenarios[scenario]
        
        try:
            # Filter prices for stress period
            stress_prices = prices.loc[start_date:end_date]
            
            if stress_prices.empty:
                return None
            
            # Calculate performance during stress period
            start_price = stress_prices.iloc[0]
            end_price = stress_prices.iloc[-1]
            
            if hasattr(start_price, 'values'):
                total_return = (end_price / start_price - 1) * 100
            else:
                total_return = (end_price / start_price - 1) * 100
            
            # Calculate maximum drawdown during period
            stress_returns = stress_prices.pct_change().dropna()
            max_dd_during_stress = self.calculate_maximum_drawdown(stress_prices)
            
            return {
                'scenario': scenario,
                'start_date': start_date,
                'end_date': end_date,
                'total_return': total_return,
                'max_drawdown': max_dd_during_stress['max_drawdown'] if max_dd_during_stress else None,
                'volatility': stress_returns.std() * np.sqrt(252) * 100 if not stress_returns.empty else None,
                'days': len(stress_prices)
            }
            
        except Exception as e:
            return None
    
    def format_output(self, ticker, analysis_results, output_format='text'):
        """Format risk analysis output"""
        if output_format == 'json':
            return json.dumps(analysis_results, indent=2, default=str)
        
        output = []
        
        if isinstance(ticker, list):
            ticker_str = ', '.join(ticker)
            title = f"⚖️ PORTFOLIO RISK ANALYSIS - {ticker_str}"
        else:
            title = f"⚖️ RISK ANALYSIS - {ticker.upper()}"
        
        output.append(title)
        output.append("=" * len(title))
        
        # Value at Risk
        if 'var_95' in analysis_results:
            var_95 = analysis_results['var_95']
            var_99 = analysis_results.get('var_99')
            
            output.append(f"\n📉 VALUE AT RISK (VaR)")
            output.append(f"1-Day VaR (95%): {var_95['var_1d']:.2f}%")
            if var_99:
                output.append(f"1-Day VaR (99%): {var_99['var_1d']:.2f}%")
            output.append(f"1-Day CVaR (95%): {var_95['cvar_1d']:.2f}%")
            
            interpretation = "Low risk" if abs(var_95['var_1d']) < 2 else "Moderate risk" if abs(var_95['var_1d']) < 4 else "High risk"
            output.append(f"Risk Level: {interpretation}")
        
        # Risk-Adjusted Returns
        if 'sharpe' in analysis_results:
            sharpe = analysis_results['sharpe']
            output.append(f"\n📊 RISK-ADJUSTED RETURNS")
            output.append(f"Sharpe Ratio: {sharpe['sharpe_ratio']:.2f}")
            output.append(f"Annual Return: {sharpe['annual_return']:.1f}%")
            output.append(f"Annual Volatility: {sharpe['annual_volatility']:.1f}%")
            
            if sharpe['sharpe_ratio'] > 1.5:
                output.append("Rating: Excellent risk-adjusted returns")
            elif sharpe['sharpe_ratio'] > 1.0:
                output.append("Rating: Good risk-adjusted returns")
            elif sharpe['sharpe_ratio'] > 0.5:
                output.append("Rating: Moderate risk-adjusted returns")
            else:
                output.append("Rating: Poor risk-adjusted returns")
        
        if 'sortino' in analysis_results:
            sortino = analysis_results['sortino']
            output.append(f"\nSortino Ratio: {sortino['sortino_ratio']:.2f}")
            output.append(f"Downside Deviation: {sortino['downside_deviation']:.1f}%")
        
        # Maximum Drawdown
        if 'max_drawdown' in analysis_results:
            dd = analysis_results['max_drawdown']
            output.append(f"\n📉 MAXIMUM DRAWDOWN")
            output.append(f"Max Drawdown: {dd['max_drawdown']:.1f}%")
            output.append(f"Peak Date: {dd['peak_date'].strftime('%Y-%m-%d')}")
            output.append(f"Trough Date: {dd['max_dd_date'].strftime('%Y-%m-%d')}")
            
            if dd['recovery_date']:
                output.append(f"Recovery Date: {dd['recovery_date'].strftime('%Y-%m-%d')}")
                output.append(f"Recovery Period: {dd['recovery_days']} days")
            else:
                output.append("Recovery: Not yet recovered")
            
            output.append(f"Current Drawdown: {dd['current_drawdown']:.1f}%")
        
        # Beta Analysis
        if 'beta' in analysis_results:
            beta = analysis_results['beta']
            output.append(f"\n🎯 BETA ANALYSIS (vs Benchmark)")
            output.append(f"Beta: {beta['beta']:.2f}")
            output.append(f"Alpha: {beta['alpha']:+.2f}%")
            output.append(f"Correlation: {beta['correlation']:.2f}")
            output.append(f"R-Squared: {beta['r_squared']:.2f}")
            
            if beta['beta'] > 1.2:
                output.append("Risk Profile: High beta (more volatile than market)")
            elif beta['beta'] > 0.8:
                output.append("Risk Profile: Market-like volatility")
            else:
                output.append("Risk Profile: Low beta (defensive)")
        
        # Correlation Matrix
        if 'correlation' in analysis_results:
            corr = analysis_results['correlation']
            output.append(f"\n🔗 CORRELATION ANALYSIS")
            output.append(f"Average Correlation: {corr['average_correlation']:.2f}")
            output.append(f"Diversification Benefit: {corr['diversification_ratio']:.2f}")
            
            # Show correlation matrix if not too large
            if corr['correlation_matrix'].shape[0] <= 5:
                output.append(f"\nCorrelation Matrix:")
                matrix = corr['correlation_matrix']
                
                # Header
                header = "       " + " ".join(f"{col:>7}" for col in matrix.columns)
                output.append(header)
                
                # Rows
                for idx, row in matrix.iterrows():
                    row_str = f"{idx:>6} " + " ".join(f"{val:>7.2f}" for val in row)
                    output.append(row_str)
        
        # Stress Testing
        if 'stress_tests' in analysis_results:
            output.append(f"\n🌪️ STRESS TEST RESULTS")
            for test in analysis_results['stress_tests']:
                if test:
                    scenario_emoji = "💥" if test['total_return'] < -20 else "📉" if test['total_return'] < -10 else "📊"
                    output.append(f"\n{scenario_emoji} {test['scenario'].upper()} ({test['start_date']} to {test['end_date']})")
                    output.append(f"  Total Return: {test['total_return']:.1f}%")
                    if test['max_drawdown']:
                        output.append(f"  Max Drawdown: {test['max_drawdown']:.1f}%")
                    if test['volatility']:
                        output.append(f"  Volatility: {test['volatility']:.1f}%")
        
        return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description='Comprehensive risk analysis for portfolios and stocks')
    parser.add_argument('tickers', help='Ticker symbol(s), comma-separated for portfolio')
    parser.add_argument('--portfolio', action='store_true', help='Treat as portfolio analysis')
    parser.add_argument('--correlation-matrix', action='store_true', help='Show correlation matrix')
    parser.add_argument('--var', action='store_true', help='Calculate Value at Risk')
    parser.add_argument('--confidence', type=float, default=95, help='VaR confidence level')
    parser.add_argument('--drawdown', action='store_true', help='Maximum drawdown analysis')
    parser.add_argument('--benchmark', default='SPY', help='Benchmark for beta calculation')
    parser.add_argument('--stress-test', action='store_true', help='Run stress tests')
    parser.add_argument('--scenario', choices=['covid', 'dotcom', 'gfc', 'black_monday', 'volmageddon'],
                       help='Specific stress test scenario')
    parser.add_argument('--all-metrics', action='store_true', help='Calculate all risk metrics')
    parser.add_argument('--period', default='2y', help='Data period (1y, 2y, 5y)')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    args = parser.parse_args()
    
    # Parse tickers
    tickers = [t.strip().upper() for t in args.tickers.split(',')]
    
    # Initialize analyzer
    analyzer = RiskAnalytics()
    
    print(f"⚖️ Analyzing risk for {', '.join(tickers)}...")
    
    # Get price data
    prices, returns = analyzer.get_price_data(tickers, args.period)
    
    if prices is None or returns is None:
        print("❌ Could not fetch price data")
        sys.exit(1)
    
    # Initialize results
    results = {}
    
    # Determine what analysis to run
    run_all = args.all_metrics or (not any([args.var, args.drawdown, args.correlation_matrix, args.stress_test]))
    
    # Single ticker analysis
    if len(tickers) == 1:
        ticker = tickers[0]
        ticker_returns = returns
        ticker_prices = prices
        
        # Value at Risk
        if args.var or run_all:
            print("📊 Calculating Value at Risk...")
            results['var_95'] = analyzer.calculate_var(ticker_returns, 95)
            results['var_99'] = analyzer.calculate_var(ticker_returns, 99)
        
        # Risk-adjusted returns
        if run_all:
            print("📈 Calculating risk-adjusted returns...")
            results['sharpe'] = analyzer.calculate_sharpe_ratio(ticker_returns)
            results['sortino'] = analyzer.calculate_sortino_ratio(ticker_returns)
        
        # Maximum drawdown
        if args.drawdown or run_all:
            print("📉 Analyzing maximum drawdown...")
            results['max_drawdown'] = analyzer.calculate_maximum_drawdown(ticker_prices)
        
        # Beta analysis
        if run_all:
            print("🎯 Calculating beta vs benchmark...")
            benchmark_prices, benchmark_returns = analyzer.get_price_data([args.benchmark], args.period)
            if benchmark_returns is not None:
                results['beta'] = analyzer.calculate_beta(ticker_returns, benchmark_returns)
        
        # Stress testing
        if args.stress_test or run_all:
            print("🌪️ Running stress tests...")
            scenarios = [args.scenario] if args.scenario else ['covid', 'gfc', 'volmageddon']
            results['stress_tests'] = []
            for scenario in scenarios:
                stress_result = analyzer.stress_test(ticker_prices, scenario)
                results['stress_tests'].append(stress_result)
    
    # Portfolio analysis
    else:
        # VaR for portfolio (using equal weights)
        if args.var or run_all:
            print("📊 Calculating portfolio VaR...")
            portfolio_returns = returns.mean(axis=1)  # Equal weighted
            results['var_95'] = analyzer.calculate_var(portfolio_returns, 95)
            results['var_99'] = analyzer.calculate_var(portfolio_returns, 99)
        
        # Correlation matrix
        if args.correlation_matrix or run_all:
            print("🔗 Calculating correlation matrix...")
            results['correlation'] = analyzer.calculate_correlation_matrix(returns)
        
        # Portfolio-level metrics
        if run_all:
            portfolio_returns = returns.mean(axis=1)
            results['sharpe'] = analyzer.calculate_sharpe_ratio(portfolio_returns)
            results['sortino'] = analyzer.calculate_sortino_ratio(portfolio_returns)
            
            portfolio_prices = (1 + portfolio_returns).cumprod()
            results['max_drawdown'] = analyzer.calculate_maximum_drawdown(portfolio_prices)
    
    # Format and display results
    output = analyzer.format_output(tickers if len(tickers) > 1 else tickers[0], results, args.format)
    print(output)


if __name__ == "__main__":
    main()
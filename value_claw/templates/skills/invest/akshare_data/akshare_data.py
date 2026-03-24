#!/usr/bin/env python3
"""Chinese market data via AKShare: A-shares, HK stocks, indices, news, macro."""

import argparse
import json
import sys
from datetime import datetime, timedelta

try:
    import akshare as ak
    import pandas as pd
except ImportError:
    print("Error: akshare not installed. Run: pip install akshare", file=sys.stderr)
    sys.exit(1)


def _fmt_num(v, default="N/A"):
    try:
        v = float(v)
        if abs(v) >= 1e12:
            return f"{v / 1e12:.2f}万亿"
        if abs(v) >= 1e8:
            return f"{v / 1e8:.2f}亿"
        if abs(v) >= 1e4:
            return f"{v / 1e4:.2f}万"
        return f"{v:.2f}"
    except (TypeError, ValueError):
        return default


def _safe(val, fmt="{}", default="N/A"):
    try:
        if val is None or (isinstance(val, float) and val != val):
            return default
        return fmt.format(val)
    except Exception:
        return default


# ── Real-time A-share quote ──────────────────────────────────────────────────

def cmd_quote(symbol: str) -> str:
    """Real-time quote for an A-share stock."""
    try:
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == symbol]
        if row.empty:
            # Try padding
            row = df[df["代码"] == symbol.lstrip("0").zfill(6)]
        if row.empty:
            return f"Error: A-share '{symbol}' not found."
        r = row.iloc[0]
        change = r.get("涨跌幅", 0)
        arrow = "▲" if float(change) >= 0 else "▼"
        lines = [
            f"{'═' * 50}",
            f"  {r.get('名称', symbol)} ({r.get('代码', symbol)})",
            f"{'═' * 50}",
            f"  最新价:   {r.get('最新价', 'N/A')}",
            f"  涨跌幅:   {arrow} {_safe(change, '{:+.2f}%')}",
            f"  涨跌额:   {_safe(r.get('涨跌额'), '{:+.2f}')}",
            f"  成交量:   {_fmt_num(r.get('成交量'))} 手",
            f"  成交额:   {_fmt_num(r.get('成交额'))}",
            f"  今开:     {r.get('今开', 'N/A')}",
            f"  最高:     {r.get('最高', 'N/A')}",
            f"  最低:     {r.get('最低', 'N/A')}",
            f"  昨收:     {r.get('昨收', 'N/A')}",
            f"  换手率:   {_safe(r.get('换手率'), '{:.2f}%')}",
            f"  市盈率:   {_safe(r.get('市盈率-动态'), '{:.2f}')}",
            f"  市净率:   {_safe(r.get('市净率'), '{:.2f}')}",
            f"  总市值:   {_fmt_num(r.get('总市值'))}",
            f"  流通市值: {_fmt_num(r.get('流通市值'))}",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"Error fetching quote for {symbol}: {exc}"


# ── Historical K-line ────────────────────────────────────────────────────────

def cmd_hist(symbol: str, period: str = "daily", start: str = None, count: int = 30) -> str:
    """Historical K-line data for an A-share."""
    if start is None:
        start = (datetime.today() - timedelta(days=365)).strftime("%Y%m%d")
    end = datetime.today().strftime("%Y%m%d")
    # akshare format: no leading zeros issue — use as-is
    try:
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period=period,
            start_date=start,
            end_date=end,
            adjust="qfq",  # Forward-adjusted (前复权)
        )
        if df.empty:
            return f"No historical data for {symbol}."

        df = df.tail(count)
        lines = [
            f"{'═' * 70}",
            f"  历史K线 ({period}): {symbol}  [前复权]  最近{count}条",
            f"{'═' * 70}",
            f"  {'日期':<12} {'开盘':>8} {'最高':>8} {'最低':>8} {'收盘':>8} {'成交量':>12} {'涨跌幅':>8}",
            f"  {'─' * 12} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 12} {'─' * 8}",
        ]
        for _, row in df.iterrows():
            date = str(row.get("日期", row.get("date", "")))[:10]
            o = _safe(row.get("开盘"), "{:.2f}")
            h = _safe(row.get("最高"), "{:.2f}")
            l = _safe(row.get("最低"), "{:.2f}")
            c = _safe(row.get("收盘"), "{:.2f}")
            vol = _fmt_num(row.get("成交量", row.get("volume")))
            pct = row.get("涨跌幅", row.get("pct_chg", ""))
            pct_str = f"{float(pct):+.2f}%" if pct != "" else "N/A"
            lines.append(f"  {date:<12} {o:>8} {h:>8} {l:>8} {c:>8} {vol:>12} {pct_str:>8}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error fetching history for {symbol}: {exc}"


# ── Company info & financial indicators ─────────────────────────────────────

def cmd_info(symbol: str) -> str:
    """Company profile and key financial indicators."""
    lines = [f"{'═' * 52}", f"  A股信息: {symbol}", f"{'═' * 52}"]
    try:
        info = ak.stock_individual_info_em(symbol=symbol)
        if not info.empty:
            lines.append("\n── 公司信息 ──────────────────────────────────")
            for _, row in info.iterrows():
                item = str(row.iloc[0])
                val = str(row.iloc[1])
                lines.append(f"  {item:<12}: {val}")
    except Exception as exc:
        lines.append(f"  公司信息获取失败: {exc}")

    try:
        fin = ak.stock_financial_analysis_indicator(symbol=symbol, start_year="2020")
        if not fin.empty:
            recent = fin.head(8)
            lines.append("\n── 财务指标 (近8期) ─────────────────────────")
            # Show key columns
            key_cols = ["日期", "每股收益", "净资产收益率", "销售净利率", "资产负债率",
                        "每股净资产", "每股经营现金流量", "营业收入同比增长率"]
            available = [c for c in key_cols if c in recent.columns]
            lines.append("  " + "  ".join(f"{c:<12}" for c in available[:5]))
            lines.append("  " + "  ".join("─" * 12 for _ in range(min(5, len(available)))))
            for _, row in recent.iterrows():
                parts = [str(row.get(c, "N/A"))[:11] for c in available[:5]]
                lines.append("  " + "  ".join(f"{p:<12}" for p in parts))
    except Exception as exc:
        lines.append(f"\n  财务指标获取失败: {exc}")

    return "\n".join(lines)


# ── Stock news ───────────────────────────────────────────────────────────────

def cmd_news(symbol: str, count: int = 10) -> str:
    """Recent news and announcements for an A-share stock."""
    try:
        df = ak.stock_news_em(symbol=symbol)
        if df.empty:
            return f"No news found for {symbol}."
        df = df.head(count)
        lines = [f"{'═' * 60}", f"  最新资讯: {symbol}", f"{'═' * 60}"]
        for _, row in df.iterrows():
            title = str(row.get("新闻标题", row.get("title", "")))[:60]
            date = str(row.get("新闻发布时间", row.get("datetime", "")))[:16]
            source = str(row.get("新闻来源", row.get("source", "")))[:12]
            url = str(row.get("新闻链接", row.get("url", "")))
            lines.append(f"\n  [{date}] {source}")
            lines.append(f"  {title}")
            if url:
                lines.append(f"  {url}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error fetching news for {symbol}: {exc}"


# ── Major indices ────────────────────────────────────────────────────────────

def cmd_indices() -> str:
    """Overview of major Chinese stock market indices."""
    try:
        df = ak.stock_zh_index_spot_em()
        targets = {
            "000001": "上证指数 (SSE Composite)",
            "399001": "深证成指 (SZSE Component)",
            "000300": "沪深300 (CSI 300)",
            "399006": "创业板指 (ChiNext)",
            "000688": "科创50 (STAR Market)",
            "399005": "中小100 (SME Board)",
        }
        lines = [
            f"{'═' * 56}",
            f"  A股主要指数实时行情",
            f"{'═' * 56}",
            f"  {'指数':<24} {'最新':>10} {'涨跌幅':>9} {'涨跌额':>9}",
            f"  {'─' * 24} {'─' * 10} {'─' * 9} {'─' * 9}",
        ]
        for code, name in targets.items():
            row = df[df["代码"] == code]
            if row.empty:
                continue
            r = row.iloc[0]
            price = _safe(r.get("最新价"), "{:.2f}")
            chg = r.get("涨跌幅", 0)
            chg_val = r.get("涨跌额", 0)
            try:
                chg_f = float(chg)
                arrow = "▲" if chg_f >= 0 else "▼"
                chg_str = f"{arrow}{abs(chg_f):.2f}%"
                chg_val_str = f"{float(chg_val):+.2f}"
            except (TypeError, ValueError):
                chg_str = "N/A"
                chg_val_str = "N/A"
            lines.append(f"  {name:<24} {price:>10} {chg_str:>9} {chg_val_str:>9}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error fetching indices: {exc}"


# ── Market overview (top movers) ─────────────────────────────────────────────

def cmd_market(top_n: int = 15) -> str:
    """Top gainers and losers in A-share market today."""
    try:
        df = ak.stock_zh_a_spot_em()
        # Remove stocks with no trading (ST, suspended, etc.)
        df = df[df["涨跌幅"].notna() & (df["成交量"] > 0)]
        df["涨跌幅"] = pd.to_numeric(df["涨跌幅"], errors="coerce")
        gainers = df.nlargest(top_n, "涨跌幅")[["代码", "名称", "最新价", "涨跌幅", "成交额"]]
        losers = df.nsmallest(top_n, "涨跌幅")[["代码", "名称", "最新价", "涨跌幅", "成交额"]]
        lines = [f"{'═' * 58}", f"  A股市场涨跌排行 (Top {top_n})", f"{'═' * 58}"]

        lines.append(f"\n── 涨幅榜 ────────────────────────────────────────")
        lines.append(f"  {'代码':<8} {'名称':<10} {'价格':>8} {'涨跌幅':>8} {'成交额':>12}")
        for _, r in gainers.iterrows():
            lines.append(
                f"  {r['代码']:<8} {str(r['名称']):<10} {_safe(r['最新价'], '{:.2f}'):>8} "
                f"{_safe(r['涨跌幅'], '{:+.2f}%'):>8} {_fmt_num(r['成交额']):>12}"
            )

        lines.append(f"\n── 跌幅榜 ────────────────────────────────────────")
        lines.append(f"  {'代码':<8} {'名称':<10} {'价格':>8} {'涨跌幅':>8} {'成交额':>12}")
        for _, r in losers.iterrows():
            lines.append(
                f"  {r['代码']:<8} {str(r['名称']):<10} {_safe(r['最新价'], '{:.2f}'):>8} "
                f"{_safe(r['涨跌幅'], '{:+.2f}%'):>8} {_fmt_num(r['成交额']):>12}"
            )
        return "\n".join(lines)
    except Exception as exc:
        return f"Error fetching market data: {exc}"


# ── HK stocks ────────────────────────────────────────────────────────────────

def cmd_hk(symbol: str) -> str:
    """Real-time quote for a Hong Kong stock."""
    try:
        df = ak.stock_hk_spot_em()
        # HK codes are typically 5 digits with leading zeros
        code = symbol.lstrip("0").zfill(5)
        row = df[df["代码"] == code]
        if row.empty:
            # Try without padding
            row = df[df["代码"].str.contains(symbol.lstrip("0"), na=False)]
        if row.empty:
            return f"Error: HK stock '{symbol}' not found. Try 5-digit code like '00700' for Tencent."
        r = row.iloc[0]
        chg = r.get("涨跌幅", 0)
        arrow = "▲" if float(chg) >= 0 else "▼"
        lines = [
            f"{'═' * 50}",
            f"  {r.get('名称', symbol)} ({r.get('代码', symbol)})  [港股]",
            f"{'═' * 50}",
            f"  最新价:   {r.get('最新价', 'N/A')} HKD",
            f"  涨跌幅:   {arrow} {_safe(chg, '{:+.2f}%')}",
            f"  今开:     {r.get('今开', 'N/A')}",
            f"  最高:     {r.get('最高', 'N/A')}",
            f"  最低:     {r.get('最低', 'N/A')}",
            f"  昨收:     {r.get('昨收', 'N/A')}",
            f"  成交量:   {_fmt_num(r.get('成交量'))}",
            f"  成交额:   {_fmt_num(r.get('成交额'))}",
            f"  总市值:   {_fmt_num(r.get('总市值'))}",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"Error fetching HK quote for {symbol}: {exc}"


# ── Sector performance ───────────────────────────────────────────────────────

def cmd_sectors() -> str:
    """A-share sector/industry performance overview."""
    try:
        df = ak.stock_sector_spot(stock="上证")
        if df.empty:
            # Try alternative
            df = ak.stock_board_industry_name_em()
            return str(df.head(20))
        lines = [
            f"{'═' * 56}",
            f"  A股板块行情",
            f"{'═' * 56}",
            f"  {'板块':<16} {'涨跌幅':>8} {'领涨股':>10}",
            f"  {'─' * 16} {'─' * 8} {'─' * 10}",
        ]
        df_sorted = df.copy()
        try:
            df_sorted["涨跌幅"] = pd.to_numeric(df_sorted.get("涨跌幅", df_sorted.get("change_pct")), errors="coerce")
            df_sorted = df_sorted.sort_values("涨跌幅", ascending=False)
        except Exception:
            pass
        for _, r in df_sorted.head(25).iterrows():
            sector = str(r.get("板块名称", r.get("sector", "")))[:15]
            chg = r.get("涨跌幅", r.get("change_pct", "N/A"))
            leader = str(r.get("领涨股票", r.get("lead_stock", "")))[:10]
            try:
                chg_str = f"{float(chg):+.2f}%"
            except (TypeError, ValueError):
                chg_str = str(chg)
            lines.append(f"  {sector:<16} {chg_str:>8} {leader:>10}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error fetching sector data: {exc}"


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Chinese market data via AKShare (A-shares, HK, indices, news, macro)."
    )
    parser.add_argument("--quote", metavar="CODE", help="Real-time A-share quote (e.g. 600519)")
    parser.add_argument("--hist", metavar="CODE", help="Historical K-line data")
    parser.add_argument("--period", default="daily", choices=["daily", "weekly", "monthly"],
                        help="K-line period for --hist (default: daily)")
    parser.add_argument("--start", metavar="YYYYMMDD", help="Start date for --hist")
    parser.add_argument("--count", type=int, default=30, help="Number of K-line bars (default: 30)")
    parser.add_argument("--info", metavar="CODE", help="Company info and financial indicators")
    parser.add_argument("--news", metavar="CODE", help="Recent stock news")
    parser.add_argument("--indices", action="store_true", help="Major index overview")
    parser.add_argument("--market", action="store_true", help="Top gainers and losers today")
    parser.add_argument("--hk", metavar="CODE", help="HK stock quote (e.g. 00700 for Tencent)")
    parser.add_argument("--sectors", action="store_true", help="Sector/industry performance")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    result = None

    if args.quote:
        result = cmd_quote(args.quote)
    elif args.hist:
        result = cmd_hist(args.hist, period=args.period, start=args.start, count=args.count)
    elif args.info:
        result = cmd_info(args.info)
    elif args.news:
        result = cmd_news(args.news)
    elif args.indices:
        result = cmd_indices()
    elif args.market:
        result = cmd_market()
    elif args.hk:
        result = cmd_hk(args.hk)
    elif args.sectors:
        result = cmd_sectors()
    else:
        parser.print_help()
        sys.exit(0)

    if result:
        print(result)


if __name__ == "__main__":
    main()

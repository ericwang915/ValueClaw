---
name: csv_analyzer
description: "Analyze CSV and Excel files — statistics, filtering, grouping, and data previews. Use when: user asks to read, analyze, query, summarize, or explore tabular data in CSV, TSV, or Excel files. NOT for: database queries, writing new files, or non-tabular formats."
dependencies: pandas, openpyxl
metadata:
  emoji: "📊"
---

# CSV Analyzer Skill

Analyze tabular data files (CSV, TSV, Excel) using pandas.

## When to Use

✅ **USE this skill when:**
- "Show me what's in data.csv"
- "First 20 rows of sales.xlsx"
- "Statistics for revenue column"
- "Filter rows where age > 30"
- "Average sales by region"
- User wants to explore, summarize, filter, or aggregate tabular data

## When NOT to Use

❌ **DON'T use this skill when:**
- Database queries (SQL) → use database tools
- Writing new CSV/Excel files → use code or spreadsheet tools
- Non-tabular formats (JSON, XML, etc.) → use appropriate parsers

## Usage/Commands

```bash
python {skill_path}/analyze.py PATH [command] [options]
```

Commands:
- `info` (default) — column types, shape, missing values
- `head` — first N rows (default 10)
- `stats` — descriptive statistics for numeric columns
- `query` — filter rows with a pandas query expression
- `groupby` — group-by aggregation
- `columns` — list column names and types

Options:
- `--rows N` — number of rows for head (default 10)
- `--query "col > 100"` — pandas query expression
- `--groupby COL` — column to group by
- `--agg mean|sum|count|min|max` — aggregation function (default: mean)
- `--format json` — output as JSON
- `--columns "col1,col2"` — select specific columns

### Examples

- "Show me what's in data.csv" → `python {skill_path}/analyze.py data.csv info`
- "First 20 rows of sales.xlsx" → `python {skill_path}/analyze.py sales.xlsx head --rows 20`
- "Average sales by region" → `python {skill_path}/analyze.py data.csv groupby --groupby region --columns sales --agg mean`

## Notes

- Install dependencies: `pip install pandas openpyxl`
- openpyxl required for Excel (.xlsx) support

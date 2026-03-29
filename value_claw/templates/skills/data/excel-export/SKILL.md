---
name: excel-export
description: >
  Export analysis data to Excel (.xlsx) or CSV files with formatted tables.
  Use when: user asks to export data to a spreadsheet, create an Excel report,
  or save analysis results to CSV/XLSX.
metadata:
  emoji: "X"
---

# Excel Export

## When to Use

- Export JSON analysis data to formatted Excel (.xlsx) files
- Create multi-sheet Excel workbooks from structured data
- Save tabular data to CSV as a lightweight alternative
- Generate formatted reports with bold headers and number formatting

## When NOT to Use

- Complex chart/graph generation (use chart-generator)
- Reading or parsing existing Excel files

## Usage

```bash
# Export JSON data to Excel
python {skill_path}/excel_export.py --input data.json --output report.xlsx

# Specify sheet name
python {skill_path}/excel_export.py --input data.json --output report.xlsx --sheet "Analysis"

# Pipe JSON from stdin
cat data.json | python {skill_path}/excel_export.py --output report.xlsx

# Force CSV output
python {skill_path}/excel_export.py --input data.json --output report.csv
```

| Option | Description |
|--------|-------------|
| `--input FILE` | JSON input file (reads stdin if omitted) |
| `--output FILE` | Output file path (.xlsx or .csv) |
| `--sheet NAME` | Sheet name (default: "Sheet1") |

## Dependencies

```bash
pip install openpyxl  # optional, falls back to CSV
```

## Notes

- Falls back to CSV if openpyxl is not installed
- Input JSON must be an array of objects or an object with array values
- Headers are auto-detected from JSON keys
- Numbers are auto-formatted in Excel output

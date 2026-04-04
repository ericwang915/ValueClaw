---
name: pdf_reader
description: "Extract text content from PDF files. Use when: user asks to read, extract, or analyze content from a PDF document. Supports multi-page extraction, page ranges, and metadata. NOT for: scanned/image PDFs (OCR), PDF editing, or creating PDFs."
dependencies: PyPDF2
metadata:
  emoji: "📄"
---

# PDF Reader Skill

Extract text and metadata from PDF files using PyPDF2.

## When to Use

✅ **USE this skill when:**
- "Read this PDF"
- "Extract pages 2-4 from report.pdf"
- "What's in this PDF?"
- "Get PDF metadata"
- User wants to read or summarize content from a PDF

## When NOT to Use

❌ **DON'T use this skill when:**
- Scanned/image PDFs (no embedded text) → use OCR tools
- PDF editing or creating → use PDF manipulation libraries
- Extracting images or embedded media → use specialized PDF tools

## Usage/Commands

```bash
python {skill_path}/read_pdf.py PATH_TO_PDF [options]
```

Options:
- `--pages 1-5` — extract only specific pages (1-indexed, supports ranges)
- `--metadata` — include PDF metadata (author, title, creation date)
- `--format json` — output as JSON
- `--summary` — show page count and character count overview only

### Examples

- "Read this PDF" → `python {skill_path}/read_pdf.py document.pdf`
- "Extract pages 2-4 from report.pdf" → `python {skill_path}/read_pdf.py report.pdf --pages 2-4`
- "What's in this PDF?" → `python {skill_path}/read_pdf.py file.pdf --summary`
- "Get PDF metadata" → `python {skill_path}/read_pdf.py file.pdf --metadata`

## Notes

- Install dependency: `pip install PyPDF2`
- Works best with PDFs that have embedded text (not scanned images)

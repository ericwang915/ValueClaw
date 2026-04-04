#!/usr/bin/env python3
"""Extract text and metadata from PDF files."""

import argparse
import json
import sys

try:
    from PyPDF2 import PdfReader
except ImportError:
    print("Error: PyPDF2 not installed.  Run: pip install PyPDF2", file=sys.stderr)
    sys.exit(1)


def parse_page_range(spec: str, total: int) -> list[int]:
    """Parse a page range like '1-5' or '2,4,6' into 0-based indices."""
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start = max(1, int(start))
            end = min(total, int(end))
            pages.update(range(start - 1, end))
        else:
            idx = int(part) - 1
            if 0 <= idx < total:
                pages.add(idx)
    return sorted(pages)


def extract_text(path: str, pages: list[int] | None = None) -> dict:
    reader = PdfReader(path)
    total = len(reader.pages)

    if pages is None:
        pages = list(range(total))

    extracted = []
    for i in pages:
        if 0 <= i < total:
            text = reader.pages[i].extract_text() or ""
            extracted.append({"page": i + 1, "text": text})

    meta_raw = reader.metadata
    metadata = {}
    if meta_raw:
        for key in ("title", "author", "subject", "creator", "producer"):
            val = getattr(meta_raw, key, None)
            if val:
                metadata[key] = str(val)
        if meta_raw.creation_date:
            metadata["created"] = str(meta_raw.creation_date)

    return {
        "path": path,
        "totalPages": total,
        "extractedPages": len(extracted),
        "metadata": metadata,
        "pages": extracted,
    }


def main():
    parser = argparse.ArgumentParser(description="Extract text from PDF files.")
    parser.add_argument("path", help="Path to the PDF file")
    parser.add_argument("--pages", default=None, help="Page range (e.g. '1-5' or '2,4,6')")
    parser.add_argument("--metadata", action="store_true", help="Show metadata only")
    parser.add_argument("--summary", action="store_true", help="Show summary only")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    try:
        reader = PdfReader(args.path)
        total = len(reader.pages)
    except Exception as exc:
        print(f"Error opening PDF: {exc}", file=sys.stderr)
        sys.exit(1)

    page_indices = None
    if args.pages:
        page_indices = parse_page_range(args.pages, total)

    data = extract_text(args.path, page_indices)

    if args.format == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if args.metadata:
        print(f"File: {args.path}  ({total} pages)")
        for k, v in data["metadata"].items():
            print(f"  {k}: {v}")
        return

    if args.summary:
        total_chars = sum(len(p["text"]) for p in data["pages"])
        print(f"File: {args.path}")
        print(f"  Pages: {total}")
        print(f"  Characters: {total_chars:,}")
        for p in data["pages"]:
            print(f"  Page {p['page']}: {len(p['text']):,} chars")
        return

    print(f"File: {args.path}  ({data['extractedPages']}/{total} pages)\n")
    for p in data["pages"]:
        print(f"--- Page {p['page']} ---")
        print(p["text"][:5000] if len(p["text"]) > 5000 else p["text"])
        print()


if __name__ == "__main__":
    main()

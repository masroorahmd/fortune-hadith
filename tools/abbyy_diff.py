#!/usr/bin/env python3
"""Compare the two OCR passes over the scan and propose readings.

The archive.org item carries the book twice over: the djvu text the parser
reads, and a second pass by ABBYY FineReader 14 inside the PDF. They fail in
different places — where one garbles a word the other often has it — so the
pair is worth more than either alone.

This tool aligns the two token by token and reports, for every token `qa.py`
could not account for, what the other pass read there. It proposes; it does not
decide. Agreement between two OCR passes is evidence, not proof: both were
trained on the same page and can be wrong together, and a proposal that looks
plausible is exactly the kind that survives review unexamined. Anything acted
on should be checked against the page image, whose number is printed here.

    tools/abbyy_diff.py              flagged entries only
    tools/abbyy_diff.py --all        every entry the two passes disagree on
    tools/abbyy_diff.py --tsv        emit correction candidates as TSV
"""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

CORPUS = Path("corpus/suhrawardy-1905.jsonl")
ABBYY = Path("corpus/raw/suhrawardy-1905.abbyy.txt")

# Scan pages holding the collection; page 52 is the preamble, 122 on is back
# matter. The printed folio runs 3 behind.
BODY_FIRST, BODY_LAST = 53, 121
PAGE_OFFSET = 3

ENTRY = re.compile(r"^\s*(\d{1,3})\s*[.,]\s+(?=\S)")
# Running heads and page numbers, which must not be taken for body text.
FURNITURE = re.compile(r"^\d+$|^[A-Z][A-Z\s',’-]{3,}$")


def load_abbyy() -> dict[int, tuple[str, int]]:
    """Return {n: (text, scan page)} from the ABBYY layer."""
    if not ABBYY.exists():
        sys.exit(
            f"missing {ABBYY} — extract it with:\n"
            "  pdftotext -layout 'The Sayings of Muhammad.pdf' "
            f"{ABBYY}"
        )
    pages = ABBYY.read_text(encoding="utf-8", errors="replace").split("\f")
    out: dict[int, tuple[list[str], int]] = {}
    for page_no in range(BODY_FIRST, min(BODY_LAST, len(pages)) + 1):
        current = None
        for line in pages[page_no - 1].split("\n"):
            s = line.strip()
            m = ENTRY.match(s)
            if m:
                current = int(m.group(1))
                out.setdefault(current, ([s[m.end():]], page_no))
            elif current and s and not FURNITURE.match(s):
                out[current][0].append(s)
    return {n: (normalise(parts), page) for n, (parts, page) in out.items()}


def normalise(parts: list[str]) -> str:
    text = " ".join(parts)
    text = re.sub(r"(\w)[-­]\s+(\w)", r"\1\2", text)  # de-hyphenate
    for a, b in (("“", '"'), ("”", '"'), ("‘", "'"), ("’", "'")):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def word_diff(old: str, new: str) -> list[tuple[str, str]]:
    """Aligned (djvu, abbyy) pairs for the stretches where the two differ."""
    a, b = old.split(), new.split()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return [
        (" ".join(a[i1:i2]), " ".join(b[j1:j2]))
        for tag, i1, i2, j1, j2 in sm.get_opcodes()
        if tag != "equal"
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true", help="not just flagged entries")
    ap.add_argument("--tsv", action="store_true", help="emit candidates as TSV")
    args = ap.parse_args()

    abbyy = load_abbyy()
    rows = [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").splitlines()]
    rows = [r for r in rows if r["series"] == "body"]

    subjects = rows if args.all else [r for r in rows if r.get("unknown")]
    absent, proposals = [], 0

    for r in rows if args.all else subjects:
        entry = abbyy.get(r["n"])
        if entry is None:
            absent.append(r["n"])
            continue
        text, page = entry
        diffs = word_diff(r["text"], text)
        if not diffs:
            continue
        unknown = set(r.get("unknown") or [])
        touching = [
            (o, n)
            for o, n in diffs
            if not unknown or any(u in o for u in unknown)
        ]
        if not touching:
            continue
        proposals += 1
        if args.tsv:
            for o, n in touching:
                print(f"{r['n']}\t{page}\t{o}\t{n}")
            continue
        print(f"--- {r['n']}  scan p{page} (folio {page - PAGE_OFFSET})"
              f"  unknown={sorted(unknown)}")
        for o, n in touching:
            print(f"      djvu  {o!r}")
            print(f"      abbyy {n!r}")
        print(f"      djvu : {r['text']}")
        print(f"      abbyy: {text}")
        print()

    if not args.tsv:
        print(f"{len(subjects)} entries examined, {proposals} with a proposal")
        if absent:
            print(f"{len(absent)} absent from the ABBYY pass too: {absent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Parse the OCR text of Suhrawardy, "The Sayings of Muhammad" (1905) into
structured entries.

Input is the archive.org djvu.txt, which contains scanning artefacts: pages
from the front matter appear up to three times, running headers and bare page
numbers are interleaved with the body, and the OCR mangles a fair number of
entry numbers.

The parser is deliberately conservative. It performs only typographic repairs
(quotes, dashes, hyphenation) and never guesses at words. Entries whose text
looks damaged are flagged rather than fixed, so that proofreading can be done
against the scan.
"""

import json
import re
import sys
from pathlib import Path

RAW = Path("corpus/raw/suhrawardy-1905.djvu.txt")
CORRECTIONS = Path("corpus/corrections.tsv")
OUT = Path("corpus/suhrawardy-1905.jsonl")

# The body starts at the last of the three scans of the opening page.
BODY_MARKER = re.compile(r"IN cop'?s NAME", re.I)
LAST_SAYING = 439

ENTRY = re.compile(r"^\s*(\d{1,3})\s*[.,]\s+(?=\S)")
# The italic "Of" of a section heading is read by the OCR as Of / OP / Oy / Ol
# / OQ) / of, so the pattern spells the variants out. What keeps the loosest
# of them safe is that the running heads have already
# been removed as page furniture by then, and that is_heading() still demands a
# predominantly upper-case topic of at most six words.
HEADING = re.compile(r"^\s*(?:O[fpyiljQ]\)?|OF|of)[;:,.]?\s*([A-Za-z][A-Za-z\s',-]{3,})$")
# The running head naming the current topic. Dropped as page furniture; left
# in, it lands in the middle of a saying.
RUNNING_TOPIC = re.compile(r"^\s*OF\s+[A-Z][A-Z\s',.-]{3,}$")
RUNNING_HEAD = re.compile(r"^\s*THE SAYINGS OF MUHAMMAD\s*$", re.I)
# Ink specks the OCR reads as punctuation at the end of a heading line. A
# heading always ends on a letter, so anything else there is debris — and it
# is not always quiet punctuation: "OfDEATH »" cost the topic The Dead.
HEADING_DEBRIS = re.compile(r"[^A-Za-z]+$")
PAGE_NO = re.compile(r"^\s*\d{1,3}\s*[A-Z]?\s*$")
# Footnote markers are a bare digit; entry numbers always carry a "." or ",".
FOOTNOTE = re.compile(r"^\s*\d{1,2}\s+[^\s.,]")
# Everything from here on is back matter, not sayings.
BACK_MATTER = re.compile(r"^\s*(GLOSSARY|APPENDIX|INDEX)\b", re.I)
# Page-number debris the OCR leaves stranded at the end of a block.
TRAILING_JUNK = re.compile(r"(?:\s+(?:\d{1,3}[A-Za-z]{0,2}|[a-z]{1,2}\d{0,2}))+$")

# Latin text that survived OCR is mostly clean; these are the mechanical fixes.
TYPO = [
    (r"[“”]", '"'),
    (r"[‘’]", "'"),
    (r"\s*—\s*", " — "),
    (r'"{2,}', '"'),
    (r"\s+", " "),
    (r"\s+([,.;:!?])", r"\1"),
]

# Signals that an entry needs a human against the scan before shipping.
SUSPECT = [
    # Anything outside ASCII except the acute accents of the transliteration
    # and the em dash, both of which corrections.tsv and clean() put there on
    # purpose. Flagging every non-ASCII character made the flag meaningless.
    (r"[^\x00-\x7FáéíóúÁÉÍÓÚ—]", "non-ascii"),
    (r"\b[a-z]{1,2}\d|\d[a-z]{1,2}\b", "digit-letter-mix"),
    # A bare digit is nearly always the mangled number of the next saying or
    # a footnote marker that leaked in; the sayings spell their numbers out.
    # Parenthesised digits are the one real use, in saying 185's enumeration.
    (r"(?<![(\d])\d", "stray-digit"),
    # An odd number of double quotes means one was lost or invented — the OCR
    # reads a footnote marker as a quote and an opening single quote as a
    # double one, both of which leave the saying visibly wrong when printed.
    (r'^(?:[^"]*"[^"]*")*[^"]*"[^"]*$', "unbalanced-quote"),
    (r"[A-Za-z]{20,}", "run-on-token"),
    (r"\b(?:[bcdfghjklmnpqrstvwxz]{5,})\b", "consonant-cluster"),
]


def heading_fixes() -> dict[str, str]:
    """Word corrections, reused here to repair mangled heading lines.

    Two headings are damaged past recognition — `Of wIpows` fails the
    upper-case test and `Of HUMIL.` is simply cut short — and both are
    corpus data, so they belong in corrections.tsv beside everything else
    rather than in a table of their own here.
    """
    global _FIXES
    if _FIXES is None:
        _FIXES = {}
        if CORRECTIONS.exists():
            for line in CORRECTIONS.read_text(encoding="utf-8").splitlines():
                if line.strip() and not line.startswith("#") and "\t" in line:
                    wrong, right = line.split("\t", 1)
                    _FIXES[wrong.strip()] = right.strip()
    return _FIXES


_FIXES: dict[str, str] | None = None


def is_heading(line: str) -> str | None:
    """Return the topic if the line is a chapter heading, else None.

    Headings are set in capitals in the original, so despite the OCR mangling
    case ("Of UsURY", "Of wIpows") they stay predominantly uppercase. Wrapped
    body lines that happen to begin with "of"/"on" are predominantly lowercase,
    which is what separates the two reliably.

    The scan leaves specks of ink at the end of a heading line, which the OCR
    reads as a stray quote or full stop — `Of THE DEAD '`. Since the pattern
    is anchored at the end of the line, one speck was enough to lose a whole
    topic and misfile every saying under it.
    """
    line = HEADING_DEBRIS.sub("", line.replace("’", "'").replace("‘", "'"))
    for wrong, right in heading_fixes().items():
        if wrong in line:
            line = re.sub(rf"(?<![A-Za-z']){re.escape(wrong)}(?![A-Za-z])", right, line)
    m = HEADING.match(line)
    if not m:
        return None
    rest = m.group(1).strip()
    letters = [c for c in rest if c.isalpha()]
    if not letters or len(rest) > 45 or len(rest.split()) > 6:
        return None
    if "," in rest or rest.endswith("-"):
        return None
    if sum(c.isupper() for c in letters) / len(letters) < 0.6:
        return None
    return titlecase(rest)


def titlecase(text: str) -> str:
    """Title-case without breaking apostrophes: GOD'S -> God's, not God'S."""
    return re.sub(
        r"[A-Za-z']+",
        lambda m: m.group(0)[0].upper() + m.group(0)[1:].lower(),
        text.lower(),
    )


def clean(text: str) -> str:
    # Normalise typography first: de-hyphenation has to see straight quotes,
    # since the OCR sometimes drops a stray one at the break ("with- 'out").
    for pat, rep in TYPO:
        text = re.sub(pat, rep, text)
    text = re.sub(r"(\w)-\s+['\"]?(\w)", r"\1\2", text)
    return text.strip()


def flags_for(text: str) -> list[str]:
    return sorted({name for pat, name in SUSPECT if re.search(pat, text)})


def blocks(lines: list[str]):
    """Group the body into blank-line-separated blocks, dropping page furniture.

    Working in blocks rather than lines is what keeps footnotes out of the
    sayings: a footnote is its own block, so it can be discarded whole instead
    of being mistaken for a continuation line.
    """
    buf: list[str] = []
    for line in lines:
        stripped = line.strip()
        if (RUNNING_HEAD.match(stripped) or PAGE_NO.match(stripped)
                or RUNNING_TOPIC.match(HEADING_DEBRIS.sub("", stripped))):
            continue
        if not stripped:
            if buf:
                yield buf
                buf = []
            continue
        buf.append(stripped)
    if buf:
        yield buf


def parse(lines: list[str]) -> list[dict]:
    entries: list[dict] = []
    topic = None
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current is not None:
            text = clean(" ".join(current["parts"]))
            text = TRAILING_JUNK.sub("", text).strip()
            if len(text) > 15:
                entries.append(
                    {
                        "n": current["n"],
                        # The body's title page carries four sayings before the
                        # first topic heading, numbered 1-4 in their own right;
                        # the collection then restarts at 1 under ABSTINENCE
                        # and runs to 439. Two series, two number 1s. Sitting
                        # under no topic is what marks the preamble out.
                        "series": "body" if current["topic"] else "preamble",
                        "topic": current["topic"],
                        "text": text,
                        "flags": flags_for(text),
                    }
                )
        current = None

    for block in blocks(lines):
        first = block[0]
        if BACK_MATTER.match(first):
            break

        if not ENTRY.match(first) and not is_heading(first) and FOOTNOTE.match(first):
            continue

        # A block is not one tidy unit: a heading and the saying that follows
        # it often share a block, as do several short sayings in a row. So each
        # line is classified on its own.
        for line in block:
            m = ENTRY.match(line)
            if m:
                flush()
                current = {
                    "n": int(m.group(1)),
                    "topic": topic,
                    "parts": [line[m.end():]],
                }
                continue
            head = is_heading(line)
            if head:
                flush()
                topic = head
                continue
            if current is not None:
                current["parts"].append(line)

    flush()
    return entries


def split_inline(entries: list[dict]) -> list[dict]:
    """Recover sayings that the scan ran into the middle of a line.

    Where a page break fell inside a paragraph the OCR sometimes drops the
    next number inline ("...the right path. 241.' The greatest enemies..."),
    which the line-based pass cannot see. Splitting is only allowed when the
    number found is exactly the successor of the current one, so ordinary
    numerals in the text cannot trigger it.
    """
    out: list[dict] = []
    for entry in entries:
        text = entry["text"]
        n = entry["n"]
        while True:
            m = re.search(
                rf"(?<=[.!?\"'])\s+{n + 1}\s*[.,]['\"]?\s+(?=[A-Z\"'])", text
            )
            if not m:
                break
            head, tail = text[: m.start()].strip(), text[m.end():].strip()
            if len(head) < 15 or len(tail) < 15:
                break
            out.append({**entry, "n": n, "text": head, "flags": flags_for(head)})
            text, n = tail, n + 1
            entry = {**entry, "n": n}
        out.append({**entry, "n": n, "text": text, "flags": flags_for(text)})
    return out


def main() -> int:
    if not RAW.exists():
        sys.exit(f"missing {RAW}")
    lines = RAW.read_text(encoding="utf-8", errors="replace").split("\n")

    starts = [i for i, l in enumerate(lines) if BODY_MARKER.search(l)]
    if not starts:
        sys.exit("could not locate start of body")
    body = lines[starts[-1] + 1:]

    entries = split_inline(parse(body))
    entries = [e for e in entries if 1 <= e["n"] <= LAST_SAYING]

    # Keep the first reading of each number; later ones are re-scanned pages.
    # Dedup within a series, not across it — the two series each have a 1, and
    # deduping globally silently swallowed the collection's first four sayings.
    seen: dict[int, dict] = {}
    preamble: dict[int, dict] = {}
    for e in entries:
        (preamble if e["series"] == "preamble" else seen).setdefault(e["n"], e)
    entries = [preamble[k] for k in sorted(preamble)] + [seen[k] for k in sorted(seen)]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    missing = [n for n in range(1, LAST_SAYING + 1) if n not in seen]
    flagged = [e["n"] for e in entries if e["flags"]]
    print(f"parsed   {len(seen)}/{LAST_SAYING} sayings -> {OUT}")
    print(f"preamble {len(preamble)} (unnumbered series on the body's title page)")
    print(f"topics   {len({e['topic'] for e in entries if e['topic']})}")
    print(f"missing  {len(missing)} (supplied from recovered.tsv by qa.py): {missing}")
    print(f"flagged  {len(flagged)}: {flagged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

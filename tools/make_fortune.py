#!/usr/bin/env python3
"""Turn the parsed corpus into a fortune cookie file.

Entries the parser flagged as OCR-damaged are held back by default: shipping a
garbled saying is worse than shipping fewer of them. Pass --include-flagged to
see them anyway while proofreading.

The eulogy after the Prophet's name is added **here**, at render time, and not
in either corpus. That is deliberate: the 1905 text is a faithful reproduction
of a public-domain book and is what the licence claim rests on, and the
modernisation is meant to diff cleanly against it. An eulogy is neither a
reading nor a register change — it is how the name is set — so it belongs to
the rendering, where it reaches both output files without touching either
source.
"""

import argparse
import json
import re
import textwrap
from pathlib import Path

SRC = Path("corpus/suhrawardy-1905.jsonl")
OUT = Path("fortune/hadith-suhrawardy")
WIDTH = 72
ATTRIB = "The Sayings of Muhammad"

EULOGY = "(saw)"
# Glued to the name rather than spaced, for the same reason the German edition
# sets it as a superscript: textwrap can break at a space, and a line that
# begins with a bare "(saw)" has separated the eulogy from what it belongs to.
# `Muhammad(saw)` is one token and cannot come apart.
#
# The possessive takes it after the `'s`, as the modern English editions set it.
# The lookahead keeps the substitution idempotent, so re-rendering an already
# eulogised string cannot produce `Muhammad(saw)(saw)`.
#
# `'s\(saw\)` has to be in that lookahead as well, or the regex defeats itself:
# against `Muhammad's(saw)` it tries the possessive, fails the lookahead, then
# **backtracks** to the bare name — where the next characters are `'s(saw)`,
# not `(saw)`, so the guard passes and the name is eulogised twice over.
NAME = re.compile(r"\bMuhammad(?:'s)?\b(?!\(saw\)|'s\(saw\))")

# The Prophet is named by epithet 55 times as well. Three things this pattern
# has to get right, none of which is obvious:
#
#   * `of God` is part of the title, so the eulogy goes after the whole phrase
#     — `the Messenger of God(saw)`, not `the Messenger(saw) of God`.
#   * where the epithet is immediately glossed with the name, only one eulogy
#     belongs there, and it belongs to the name: `the Rasúl (Muhammad(saw))`.
#   * **saying 134 is about other prophets** — "There was not any Messenger
#     sent before me by God to mankind" — and they take `(as)`, never `(saw)`.
#     `any Messenger` is the generic use and is excluded. This is the one place
#     in the corpus where the same word means someone else, and eulogising it
#     would be a doctrinal error, not a typographic one.
#
# The name pass runs first, so the lookarounds here can see its output: that is
# how `Muhammad(saw) The Prophet` — eleven of the book's section headings —
# avoids collecting a second eulogy.
# `messenger` is listed in lower case as well: saying 57 has the Prophet call
# himself "the servant of God, and His messenger", and 199 "God and His
# messenger". The plurals — "the other messengers of God", "inferior to the
# prophets" — are other prophets, and the trailing `\b` is what keeps them out.
EPITHET = re.compile(
    r"(?<!any )(?<!\(saw\) The )"
    r"\b(?:Rasúl|Messenger|messenger|Apostle|Prophet)(?:'s)?(?:\s+of\s+God)?\b"
    r"(?!\(saw\)|'s\(saw\)| \(Muhammad|'s \(Muhammad)")


def eulogise(text: str) -> str:
    text = NAME.sub(lambda m: m.group(0) + EULOGY, text)
    return EPITHET.sub(lambda m: m.group(0) + EULOGY, text)


def render(entry: dict, field: str, eulogy: bool = True) -> str:
    body = entry.get(field) or entry["text"]
    if eulogy:
        body = eulogise(body)
    body = "\n".join(textwrap.wrap(body, WIDTH))
    # The book numbers two series: four sayings on the body's title page, then
    # the collection proper starting again at 1. Citing both as "No. 1" would
    # point a reader at the wrong page.
    if entry.get("series") == "preamble":
        ref = f"{ATTRIB}, Preamble No. {entry['n']}"
    else:
        ref = f"{ATTRIB}, No. {entry['n']}"
    if entry["topic"]:
        ref += f" ({entry['topic']})"
    # The whole reference line, not just the book title: eleven of the book's
    # section headings are named after the Prophet — `Muhammad The Prophet's
    # Kindness` — and eulogising only the attribution left those bare.
    return f"{body}\n{' ' * 8}-- {eulogise(ref) if eulogy else ref}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-flagged", action="store_true")
    ap.add_argument("--no-eulogy", action="store_true",
                    help="omit the (saw) after the Prophet's name")
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--field", default="modern",
                    help="which text to ship. `modern` falls back to the 1905 "
                         "text for any entry the modernisation left alone, so "
                         "a partial pass still produces a complete file")
    ap.add_argument("--max-length", type=int, default=0,
                    help="drop entries longer than this many characters")
    args = ap.parse_args()

    entries = [json.loads(l) for l in args.src.read_text(encoding="utf-8").splitlines()]
    field = args.field
    if not any(e.get(field) for e in entries):
        print(f"note     no `{field}` text in {args.src}; shipping the 1905 text")
    total = len(entries)

    kept = entries if args.include_flagged else [e for e in entries if not e["flags"]]
    dropped_flagged = total - len(kept)

    dropped_long = 0
    if args.max_length:
        before = len(kept)
        kept = [e for e in kept if len(e["text"]) <= args.max_length]
        dropped_long = before - len(kept)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    rendered = "\n%\n".join(render(e, field, not args.no_eulogy) for e in kept) + "\n%\n"
    args.out.write_text(rendered, encoding="utf-8")

    print(f"wrote    {len(kept)} of {total} entries -> {args.out}")
    if not args.no_eulogy:
        # Counted on the output rather than the source: the reference line
        # carries the name too, and eleven section headings carry it again.
        left = len(NAME.findall(rendered))
        print(f"eulogy   {rendered.count(EULOGY)} times" +
              (f", but {left} mentions were missed" if left else ""))
    if dropped_flagged:
        print(f"held     {dropped_flagged} flagged as OCR-damaged")
    if dropped_long:
        print(f"dropped  {dropped_long} over {args.max_length} characters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

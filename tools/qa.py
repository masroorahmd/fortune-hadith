#!/usr/bin/env python3
"""Apply curated OCR corrections and report what still needs a human.

Writes the corrected corpus back to the JSONL and prints the tokens that no
dictionary, allowlist or correction accounts for. Those are the entries that
have to be checked against the scan before the corpus can ship.

Also merges in `recovered.tsv`, the sayings the OCR lost outright. They were
read off the page images rather than repaired, so they arrive already proofed
— but they still go through the unknown-token check here, on the principle
that a transcription is no more trustworthy than an OCR pass until something
has looked at it.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_suhrawardy import flags_for  # noqa: E402
from modernise import derive_eth  # noqa: E402

# Debris the word-level checks cannot see, because none of it is a word. Every
# one of these was found in a corpus that this file was reporting as clean:
# what the unknown-token check looks at is tokens, so a footnote marker, a
# running head or half of the next saying passes it untouched.
DEBRIS = [
    ("stray symbol", re.compile(r"[$§@#~^_|\\{}<>\[\]&*]")),
    ("unfinished", re.compile(r"[^.!?\"')]\s*$")),
    ("quote debris", re.compile(r"\?\"'|\"\s*'|'\s*\"|\?'\"")),
    ("running head", re.compile(r"\bO[Ff]\s+[A-Z]{3,}")),
    # A speck of ink before a word reads as an opening quote. It has to be a
    # lower-case word to be worth reporting: the transliterations genuinely
    # begin with one — 'A'ishah, 'Uthmán, 'Amir — and they are capitalised.
    ("stray apostrophe", re.compile(r"(?<=\s)'(?=[a-z])")),
]

CORPUS = Path("corpus/suhrawardy-1905.jsonl")
CORRECTIONS = Path("corpus/corrections.tsv")
RECOVERED = Path("corpus/recovered.tsv")
PROOFED = Path("corpus/proofed.tsv")
ARTEFACTS = Path("corpus/artefacts.tsv")
ALLOWLIST = Path("corpus/known-words.txt")
DICTS = [
    Path("/usr/share/dict/british-english"),
    Path("/usr/share/dict/american-english"),
]
ARCHAIC = re.compile(r"(eth|est)$")


def load_corrections() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in CORRECTIONS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "\t" not in line:
            continue
        wrong, right = line.split("\t", 1)
        out[wrong.strip()] = right.strip()
    return out


def load_words() -> set[str]:
    words: set[str] = set()
    for d in DICTS:
        if d.exists():
            words |= {
                w.strip().lower()
                for w in d.read_text(encoding="utf-8", errors="replace").splitlines()
            }
    if ALLOWLIST.exists():
        words |= {
            w.split("#")[0].strip().lower()
            for w in ALLOWLIST.read_text(encoding="utf-8").splitlines()
            if w.split("#")[0].strip()
        }
    return words


def read_scan_tsv(path: Path) -> dict[int, dict]:
    """Read an `n / scan page / topic / text` file transcribed from the images."""
    out: dict[int, dict] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        n, page, topic, text = line.split("\t", 3)
        # A leading P marks the preamble series, whose numbers collide with the
        # collection's own.
        series = "preamble" if n.startswith("P") else "body"
        key = (series, int(n.lstrip("P")))
        out[key] = {
            "n": key[1],
            "series": series,
            "topic": None if topic.strip() == "-" else topic.strip(),
            "text": text.strip(),
            "flags": [],
            "source": f"scan p{page.strip()}",
        }
    return out


def merge_recovered(entries, recovered):
    """Insert the recovered sayings, without displacing anything parsed.

    If a number turns up in both, the parse wins and the recovered line is
    reported as redundant rather than applied — a saying that parses is no
    longer missing, and silently overwriting it would hide that the file has
    gone stale.

    Returns (merged, added, redundant).
    """
    have = {(e["series"], e["n"]) for e in entries}
    added = sorted(k for k in recovered if k not in have)
    redundant = sorted(k for k in recovered if k in have)
    merged = entries + [recovered[k] for k in added]
    merged.sort(key=lambda e: (e["series"] != "preamble", e["n"]))
    return merged, added, redundant


def load_artefacts() -> list[tuple[str, int, str, str, int, str]]:
    """Anchored single edits from artefacts.tsv, in file order."""
    out = []
    if not ARTEFACTS.exists():
        return out
    for line in ARTEFACTS.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        num = parts[0].strip()
        series = "preamble" if num.upper().startswith("P") else "body"
        page = int(parts[3]) if len(parts) > 3 and parts[3].strip() else 0
        note = parts[4].strip() if len(parts) > 4 else ""
        out.append((series, int(num.lstrip("Pp")), parts[1], parts[2], page, note))
    return out


def apply_artefacts(entries: list[dict], repairs: list) -> tuple[int, int, list[str], list[str], set[str]]:
    """Apply each repair to its entry, refusing anything that is not exact.

    A repair whose `find` matches twice is ambiguous and would be a guess, and
    one whose `find` is absent while its replacement is absent too has outlived
    the defect it worked around. Neither is applied, and both are reported, on
    the same principle as the redundant check for recovered.tsv.

    Returns (applied, already-present, stale, ambiguous, reviewed).
    """
    index = {(e["series"], e["n"]): e for e in entries}
    applied, done, stale, ambiguous, reviewed = 0, 0, [], [], set()
    for series, n, find, repl, page, _note in repairs:
        e = index.get((series, n))
        where = f"{series}{n}"
        if e is None:
            stale.append(f"{where} (no such entry)")
            continue
        # `OK` records that the entry was opened at the page and is right as it
        # stands. The debris sweep then reports the unreviewed rather than the
        # merely flagged, which is the difference between a check that stays
        # useful and one that everyone learns to ignore.
        if find == "OK":
            reviewed.add(where)
            continue
        hits = e["text"].count(find)
        if hits == 0:
            # `find` gone can mean two things, and conflating them makes the
            # report useless: the repair has already been applied — qa.py
            # rewrites the JSONL in place, so a second run over its own output
            # sees only repaired text — or the defect went away upstream and
            # the line is dead. The replacement being present settles it,
            # except for a deletion, which leaves nothing to look for.
            if not repl or repl in e["text"]:
                done += 1
            else:
                stale.append(where)
        elif hits > 1:
            ambiguous.append(f"{where} ({hits}x {find!r})")
        else:
            e["text"] = e["text"].replace(find, repl)
            e["artefact_page"] = page
            applied += 1
    return applied, done, stale, ambiguous, reviewed


def apply_corrections(text: str, table: dict[str, str]) -> str:
    if not table:
        return text
    pattern = re.compile(
        r"(?<![A-Za-z'])(" + "|".join(re.escape(k) for k in sorted(table, key=len, reverse=True)) + r")(?![A-Za-z])"
    )
    return pattern.sub(lambda m: table[m.group(1)], text)


def unknown_tokens(text: str, words: set[str]) -> list[str]:
    out = []
    for raw in re.findall(r"[A-Za-zÁÀÂÄáàâäÍíÚúÛüÓóÔöÉéÊë']{2,}", text):
        # the OCR renders opening quotes as apostrophes, so they stick to words
        tok = raw.strip("'")
        if len(tok) < 2:
            continue
        low = tok.lower()
        # An -eth ending used to be waved through on sight, which made every
        # archaic-looking token invisible to this check. `secketh`, `cateth`
        # and `sceth` are all OCR damage that lived in the corpus because of
        # it. An archaic verb form only counts as real if a base verb for it
        # exists; otherwise it is damage wearing archaism as a disguise.
        if low in words or low.rstrip("'s") in words:
            continue
        if low.endswith("eth") and derive_eth(low, words):
            continue
        if ARCHAIC.search(low) and not low.endswith("eth"):
            continue
        # transliterated forms carry diacritics; treat them as intentional
        if re.search(r"[áàâäíúûóôéê]", low):
            continue
        out.append(tok)
    return out


def main() -> int:
    table = load_corrections()
    words = load_words()
    entries = [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").splitlines()]
    entries, added, redundant = merge_recovered(entries, read_scan_tsv(RECOVERED))
    proofed = read_scan_tsv(PROOFED)

    changed = 0
    for e in entries:
        fixed = apply_corrections(e["text"], table)
        if fixed != e["text"]:
            changed += 1
            e["text"] = fixed

    # The anchored repairs land after the corrections, so that they can be
    # written against the text a reviewer actually reads: anchoring `Islám?"'`
    # on the raw parse would have meant writing `Islim?"'`, which is a spelling
    # nothing in the corpus contains once qa.py has run. They land before the
    # proofread transcriptions, because those replace an entry outright and
    # leave nothing to anchor to.
    art_applied, art_done, art_stale, art_amb, art_ok = apply_artefacts(entries, load_artefacts())

    for e in entries:
        # Proofread text is the transcription of the page and replaces whatever
        # the OCR produced. It lands after the corrections so that no
        # substitution can reach into it, and before the unknown-token check so
        # that it is still held to the same standard as everything else.
        if (e["series"], e["n"]) in proofed:
            p = proofed[(e["series"], e["n"])]
            e["text"], e["topic"], e["source"] = p["text"], p["topic"], p["source"]
            e["flags"] = [f for f in e["flags"] if f == "needs-proofing"]
        # The structural flags were set on the raw parse. Corrections and
        # proofreading are exactly what clears the characters they look for, so
        # they have to be taken again here or they go stale and hold back text
        # that is no longer damaged.
        e["flags"] = flags_for(e["text"])
        e["unknown"] = sorted(set(unknown_tokens(e["text"], words)))
        if e["unknown"] and "needs-proofing" not in e["flags"]:
            e["flags"] = sorted(set(e["flags"]) | {"needs-proofing"})
        elif not e["unknown"]:
            e["flags"] = [f for f in e["flags"] if f != "needs-proofing"]

    with CORPUS.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    remaining = [e for e in entries if e["unknown"]]
    tokens: dict[str, int] = {}
    for e in remaining:
        for t in e["unknown"]:
            tokens[t] = tokens.get(t, 0) + 1

    print(f"recovered  {len(added)} sayings merged from {RECOVERED.name}: {[k[1] for k in added]}")
    print(f"proofed    {len(proofed)} entries replaced from {PROOFED.name}")
    if redundant:
        print(f"redundant  {len(redundant)} now parse on their own: {[k[1] for k in redundant]}")
    print(f"artefacts  {art_applied} anchored repairs from {ARTEFACTS.name}")
    if art_done:
        print(f"           {art_done} already present — qa.py was run over its own output")
    if art_stale:
        print(f"stale      {len(art_stale)} repairs matched nothing: {', '.join(art_stale)}")
    if art_amb:
        print(f"ambiguous  {len(art_amb)} repairs matched more than once, not applied:")
        for a in art_amb:
            print(f"    {a}")
    print(f"corrected  {changed} of {len(entries)} entries")
    print(f"clean      {len(entries) - len(remaining)}")
    print(f"to proof   {len(remaining)} entries, {len(tokens)} distinct tokens")
    print()
    for tok, n in sorted(tokens.items(), key=lambda x: (-x[1], x[0]))[:40]:
        nums = [e["n"] for e in remaining if tok in e["unknown"]][:6]
        print(f"  {n:3d}  {tok:20s} in {nums}")

    print()
    print("debris     not a token, so nothing above looks at it:")
    dirty: set[str] = set()
    for name, pat in DEBRIS:
        who = [f"{e['series']}{e['n']}" for e in entries
               if pat.search(e["text"]) and f"{e['series']}{e['n']}" not in art_ok]
        dirty |= set(who)
        print(f"  {name:14} {len(who):3}  {' '.join(who[:12])}{' ...' if len(who) > 12 else ''}")
    print(f"  {'UNREVIEWED':14} {len(dirty):3}")
    print(f"  {'reviewed':14} {len(art_ok):3}  flagged, opened at the page, correct as it stands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

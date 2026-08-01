#!/usr/bin/env python3
"""Check that the modernised text says what the 1905 text said.

The rules engine cannot invent content, so this exists for the model engine.
A model asked to change the register will sometimes change the claim as well —
soften an imperative, drop a clause it read as redundant, gloss a term — and
those edits are invisible in a fluent-looking sentence. This finds them
mechanically:

  names       every capitalised word and every number must survive unchanged.
              A dropped `Rasúl` or a `nine things` that became `ten` is the
              failure that matters most in a hadith corpus.
  dropped     content words in the 1905 text with no counterpart in the modern
              one, after the lexicon and the -eth derivation are accounted for
  added       content words in the modern text that came from nowhere
  length      a ratio far from 1 means something was summarised or padded
  quotes      the corpus quotes speakers; an unbalanced or vanished quotation
              mark means a reported saying has become the narrator's
  register    archaisms the pass was supposed to remove and did not

Nothing here decides anything. It says which entries a human has to read, in
the same spirit as qa.py: never silently drop or auto-fix, flag and report.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from modernise import load_lexicon, load_dict, derive_eth  # noqa: E402

# Function words are free to appear or vanish: modernising "Kill not" to
# "Do not kill" adds `do`, and "that which" to "what" removes two.
FUNCTION = set("""
a an the and or but if then than that this these those there here of to in on at by for
with from as is are was were be been being am do does did doing done have has had having
not no nor so such it its he him his she her they them their we us our you your i me my
who whom whose which what when where why how all any both each few more most other some
only own same too very can will just should now up down out off over under again further
once about against between into through during before after above below shall may might
must would could one will towards toward upon
""".split())

def _american_only() -> set[str]:
    def read(p: str) -> set[str]:
        try:
            return {w.strip().lower() for w in open(p, encoding="utf-8", errors="ignore")}
        except OSError:
            return set()
    br, am = read("/usr/share/dict/british-english"), read("/usr/share/dict/american-english")
    return (am - br) if br and am else set()


AMERICAN_ONLY = _american_only()

ARCHAIC = re.compile(
    r"\b(?:\w+eth|thou|thee|thy|thine|ye|hath|doth|saith|hast|dost|art|shalt|wilt|"
    r"didst|verily|unto|whoso\w*|betwixt|whereby|wherein|whereof|nay)\b", re.I)


def words_of(text: str) -> list[str]:
    # The apostrophe has to stay inside the word for "God's", but the scan
    # leaves stray ones against the word edges, and those made every quoted
    # substitution read as a dropped word.
    return [w.strip("'") for w in re.findall(r"[A-Za-zÀ-ÿ']+", text) if w.strip("'")]


def names_and_numbers(text: str) -> tuple[set[str], list[str]]:
    """Capitalised words that are not sentence-initial, plus every numeral.

    Sentence-initial capitals are excluded because modernising the syntax
    legitimately changes which word starts the sentence.
    """
    names = set()
    for m in re.finditer(r"(?<![.!?\"“]\s)(?<!^)\b([A-ZÀ-Þ][a-zà-ÿ'´]{1,})\b", text, re.M):
        names.add(m.group(1))
    return names, re.findall(r"\d+", text)


def build_expected(subs: dict[str, str]) -> dict[str, set[str]]:
    """archaic form -> the words the pass is allowed to turn it into.

    A value can be several words — `whereof` becomes `of which` — so the
    mapping is to a set, or the substitution reads as a dropped word.
    """
    return {k.lower(): set(words_of(v.lower())) for k, v in subs.items()}


def check(entry: dict, subs: dict[str, str], dic: set[str],
          expected: dict[str, set[str]]) -> list[str]:
    old, new = entry["text"], entry.get("modern")
    if not new:
        return ["missing: no modern text"]
    problems = []

    # `Thy` and `Verily` are capitalised mid-sentence after a quotation mark,
    # so the name test sees the lexicon doing its job as a lost proper noun.
    # Canonicalise the old side first; what is left is a real name.
    def as_names(text: str) -> set[str]:
        out = set()
        for w in names_and_numbers(text)[0]:
            repl = expected.get(w.lower())
            out |= {r.capitalize() for r in repl} if repl else {w}
        return out

    o_names, o_nums = as_names(old), names_and_numbers(old)[1]
    n_names, n_nums = as_names(new), names_and_numbers(new)[1]
    lost = o_names - n_names
    if lost:
        problems.append(f"names dropped: {', '.join(sorted(lost))}")
    gained = n_names - o_names
    if gained:
        problems.append(f"names added: {', '.join(sorted(gained))}")
    if o_nums != n_nums:
        problems.append(f"numbers changed: {o_nums} -> {n_nums}")

    def canon(w: str) -> set[str]:
        lw = w.lower()
        if lw in expected:
            return expected[lw]          # `whereof` -> {of, which}
        if lw.endswith("eth"):
            got = derive_eth(lw, dic)
            if got:
                return {got}
        return {lw}

    o_set = set().union(*(canon(w) for w in words_of(old))) - FUNCTION
    n_set = {w.lower() for w in words_of(new)} - FUNCTION
    # A word survives if it is there, or if its stem is: "remembrance" may
    # legitimately become "remembering".
    def covered(w: str, pool: set[str]) -> bool:
        if w in pool:
            return True
        stem = w[:5]
        return len(w) > 5 and any(p.startswith(stem) for p in pool)

    dropped = sorted(w for w in o_set if not covered(w, n_set))
    added = sorted(w for w in n_set if not covered(w, o_set))
    if dropped:
        problems.append(f"dropped: {', '.join(dropped)}")
    if added:
        problems.append(f"added: {', '.join(added)}")

    ratio = len(new) / max(len(old), 1)
    if not 0.75 <= ratio <= 1.3:
        problems.append(f"length ratio {ratio:.2f}")

    if old.count('"') != new.count('"'):
        problems.append(f"quote marks {old.count(chr(34))} -> {new.count(chr(34))}")

    # Suhrawardy spells British — `honoureth`, `splendour`, `labour` — and a
    # model rewriting a sentence quietly switches to its own default. Eight
    # such words entered a 74-entry qwen3:32b pass (`fulfill`, `rumors`,
    # `travelers`), none of which any content check would ever notice.
    us = sorted({w.lower() for w in words_of(new)} & AMERICAN_ONLY
                - {w.lower() for w in words_of(old)})
    if us:
        problems.append(f"US spelling: {', '.join(us)}")

    left = ARCHAIC.findall(new)
    left = [w for w in left if not re.fullmatch(r"\w*(?:best|guest|rest|quest|teeth)", w, re.I)]
    if left:
        problems.append(f"still archaic: {', '.join(sorted(set(left)))}")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path, nargs="?",
                    default=Path("corpus/suhrawardy-modern.jsonl"))
    ap.add_argument("--verbose", action="store_true",
                    help="print the 1905 and modern text of every flagged entry")
    ap.add_argument("--engine", default="", help="check only entries from this engine")
    args = ap.parse_args()

    subs, _ = load_lexicon()
    dic = load_dict()
    expected = build_expected(subs)

    rows = [json.loads(l) for l in args.src.read_text(encoding="utf-8").splitlines()]
    if args.engine:
        rows = [r for r in rows if args.engine in (r.get("engine") or "")]

    flagged = 0
    kinds: dict[str, int] = {}
    for r in rows:
        problems = check(r, subs, dic, expected)
        if not problems:
            continue
        flagged += 1
        for p in problems:
            kinds[p.split(":")[0].split(" ")[0]] = kinds.get(p.split(":")[0].split(" ")[0], 0) + 1
        print(f"{r['series']}{r['n']}  [{r.get('engine', '?')}]")
        for p in problems:
            print(f"    {p}")
        if args.verbose:
            print(f"    1905: {r['text']}")
            print(f"    now : {r.get('modern')}")

    print()
    print(f"checked  {len(rows)}")
    print(f"flagged  {flagged}")
    for k, n in sorted(kinds.items(), key=lambda x: -x[1]):
        print(f"  {k:10} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Turn Suhrawardy's 1905 English into contemporary English.

This is a register change, not a translation. The semantic work was done by a
human in 1905, the original sits beside the result in the JSONL, and every
divergence shows up in a diff — which is why this is worth doing where a fresh
translation from Arabic is not.

Two engines, because the problem has two halves that do not answer to the same
method:

  rules   deterministic word-level substitution from corpus/modern-lexicon.tsv
          plus the -eth verbs derived against the system dictionary. Reviewable,
          repeatable, and it cannot invent text. It reaches the morphology and
          stops there.

  model   an instructed model rewrites the sentence. It reaches the syntax the
          rules cannot — negative imperatives, "that which", the inversions —
          and it can also silently change the meaning, which is what
          modernise_check.py exists to catch.

Run `--engine rules --report` first: the residue it prints is the exact set of
entries that need the second engine, and it is a good deal smaller than the
corpus.
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CORPUS = Path("corpus/suhrawardy-1905.jsonl")
LEXICON = Path("corpus/modern-lexicon.tsv")
HAND = Path("corpus/modernised.tsv")
OUT = Path("corpus/suhrawardy-modern.jsonl")
DICTS = [
    Path("/usr/share/dict/british-english"),
    Path("/usr/share/dict/american-english"),
]

ENDPOINTS = {
    "ollama": "http://localhost:11434/v1/chat/completions",
    "lmstudio": "http://localhost:1234/v1/chat/completions",
}

SYSTEM = (
    "You rewrite Victorian-era English into clear contemporary English. "
    "This is a change of register only. Do not translate, interpret, explain, "
    "modernise the ideas, soften anything, or add or remove any content. "
    "Keep every proper name, number and parenthetical exactly as given, "
    "including transliterations such as Rasul and Iman. Keep quotation marks "
    "where the original quotes someone. Address to God keeps its capital: "
    "Thou and Thee become You, Thy becomes Your. Replace archaic verb forms "
    "(hath, doth, payeth, seeketh), archaic pronouns (thou, thee, thy, ye), "
    "and archaic constructions ('Kill not' -> 'Do not kill', 'that which' -> "
    "'what'). Keep the sentence order and the sentence count. Write plain "
    "prose without contractions: 'is not', never 'isn't'. "
    "Output the rewritten text only, with no preamble, notes or explanation."
)

USER = "Rewrite this saying in contemporary English:\n\n{text}"

# Syntax the word-level engine provably cannot reach. Each of these leaves a
# sentence that is grammatical but still reads as 1905, so they are the
# handover point to the model rather than defects in the lexicon.
RESIDUE = [
    # Two versions of this rule were wrong before this one, both by being too
    # clever about the context:
    #
    #   - it excluded `not the`, meant to spare "not the only" and in fact
    #     sparing every negative imperative that has an object, which is most
    #     of them. `Fear not the obloquy` sat unflagged behind that.
    #   - it required the verb to start a clause. But the construction is not
    #     confined to imperatives: `He whom prayer prevents not from
    #     wrongdoing`, `He dies not who gives life to learning`, `you gave it
    #     Me not` are all mid-sentence, and all twelve of that kind were
    #     missed.
    #
    # What actually marks the construction is a lexical verb immediately before
    # `not`. `do not` and `must not` are already modern, so the auxiliaries are
    # what gets excluded — nothing about position.
    ("neg-imperative", re.compile(
        r"\b(?!(?:do|does|did|must|will|shall|may|might|can|could|is|are|was|were|am|be|been|"
        r"has|have|had|should|would|need|dare)\b)"
        r"([a-z]+)\s+not\b(?!\s+(?:only|to|be)\b)", re.I)),
    ("that-which", re.compile(r"\bthat which\b|\bthose which\b", re.I)),
    ("inversion", re.compile(r"\bfor him (?:are|is)\b|\bthere (?:is|are) no\w* \w+, no\b", re.I)),
    ("archaic-idiom", re.compile(
        r"\b(?:heed|nigh|forsake|forsook|beseech|behold|alms|countenance|"
        r"cherisher|abideth|hearken|bade|thereof|therein|whereupon)\b", re.I)),
    ("used-to", re.compile(r"\bused to \w+\b")),
    # "Solve Thou my difficulties" and "O Thou Most Merciful": here `Thou` is
    # not a pronoun to be swapped but a construction to be dropped, and
    # substituting `You` makes the sentence worse than it was.
    ("thou-as-subject", re.compile(r"\bO (?:Thou|You)\b|(?:^|[.;!?]\s+)[A-Z][a-z]+ (?:Thou|You)\b")),
]


# --------------------------------------------------------------------------
# rules engine


def load_lexicon() -> tuple[dict[str, str], dict[str, str]]:
    """Return (substitutions, notes). Keys are matched case-sensitively."""
    subs: dict[str, str] = {}
    notes: dict[str, str] = {}
    for line in LEXICON.read_text(encoding="utf-8").splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        subs[parts[0]] = parts[1]
        if len(parts) > 2 and parts[2].strip():
            notes[parts[0]] = parts[2].strip()
    return subs, notes


def load_hand() -> dict[tuple[str, int], str]:
    """Hand-written rewrites, keyed the way proofed.tsv is keyed.

    These override the rules output rather than feed it, because the entries
    that reach this file are ones where a word-level pass produced something
    worse than the original.
    """
    out: dict[tuple[str, int], str] = {}
    if not HAND.exists():
        return out
    for line in HAND.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "\t" not in line:
            continue
        num, text = line.split("\t", 1)
        num = num.strip()
        series = "preamble" if num.upper().startswith("P") else "body"
        out[(series, int(num.lstrip("Pp")))] = text.strip()
    return out


def load_dict() -> set[str]:
    words: set[str] = set()
    for p in DICTS:
        if p.exists():
            words |= {w.strip().lower() for w in p.read_text(
                encoding="utf-8", errors="ignore").splitlines()}
    if not words:
        sys.exit(f"no system dictionary found; looked in {[str(p) for p in DICTS]}")
    return words


def third_person(base: str) -> str:
    if re.search(r"(s|x|z|ch|sh|o)$", base):
        return base + "es"          # go -> goes, not gos
    if re.search(r"[^aeiou]y$", base):
        return base[:-1] + "ies"
    return base + "s"


def derive_eth(word: str, words: set[str]) -> str | None:
    """`loveth` -> `loves`, by finding the base verb in the dictionary.

    The obvious rule — drop `eth`, add `s` — gets `cometh` to `coms` and
    `knoweth` to `knowes`. The stem is ambiguous because Victorian spelling
    dropped the silent `e`, so the dictionary decides which base is real. Order
    matters: `care` must be tried before `car`, or `careth` becomes `cars`.

    Returns None when no base exists, which in this corpus has meant OCR damage
    rather than an unusual verb — see the foot of modern-lexicon.tsv.
    """
    stem = word[:-3]
    cands = [stem + "e", stem]
    if len(stem) > 2 and stem[-1] == stem[-2] and stem[-1] not in "aeiou":
        cands.append(stem[:-1])          # committ -> commit
    for base in cands:
        # A base with no vowel is not a word however firmly the wordlist says
        # otherwise: `sc` is in it, which turned the OCR's `sceth` into `scs`
        # and hid a damaged saying from qa.py.
        if base in words and re.search(r"[aeiouy]", base):
            return third_person(base)
    return None


def apply_case(src: str, repl: str) -> str:
    if src[:1].isupper() and not repl[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


def modernise_rules(text: str, subs: dict[str, str], words: set[str],
                    unresolved: list[str] | None = None) -> str:
    # `thine`/`mine` before a vowel or `h` are determiners, not pronouns:
    # "mine enemies" is "my enemies" but "the fault is mine" stays.
    text = re.sub(r"\bthine\b(?=\s+[aeiouhAEIOUH])", "your", text)
    text = re.sub(r"\bThine\b(?=\s+[aeiouhAEIOUH])", "Your", text)
    text = re.sub(r"\bmine\b(?=\s+[aeiouhAEIOUH])", "my", text)
    # `save` is only archaic as a preposition, which in this corpus always
    # follows a comma: "no strength, save in Thee".
    text = re.sub(r"(,\s*)\bsave\b(?=\s+(?:in|for|by|with|through|that|what|when)\b)",
                  r"\1except", text)

    def one(m: re.Match) -> str:
        w = m.group(0)
        if w in subs:
            return subs[w]
        if w.lower() in subs:
            return apply_case(w, subs[w.lower()])
        if w.lower().endswith("eth"):
            got = derive_eth(w.lower(), words)
            if got:
                return apply_case(w, got)
            if unresolved is not None:
                unresolved.append(w)
        return w

    return re.sub(r"\b[A-Za-z]+\b", one, text)


def residue(text: str) -> list[str]:
    return [name for name, pat in RESIDUE if pat.search(text)]


# --------------------------------------------------------------------------
# model engine


def strip_reasoning(text: str) -> str:
    """Remove <think> blocks. An unclosed one means the model never answered."""
    text = re.sub(r"(?s)<think>.*?</think>", "", text)
    text = re.sub(r"(?s)^.*?</think>", "", text)
    if "<think>" in text:
        raise RuntimeError("unterminated <think> block: model never answered")
    return text.strip()


def call(endpoint: str, model: str, text: str, timeout: int) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER.format(text=text)},
        ],
        "temperature": 0.2,
        "stream": False,
    }
    req = urllib.request.Request(
        endpoint, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # The status alone is useless here: a 400 from LM Studio is usually
        # "could not load the model", which is a VRAM problem, not a bad request.
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from None
    msg = body["choices"][0]["message"]
    out = strip_reasoning(msg.get("content") or "")
    if not out:
        raise RuntimeError("empty content (reasoning model spent the budget?)")
    # Models like to wrap the answer in quotes even when told not to.
    if out[0] in "“\"" and out[-1] in "”\"" and out.count('"') <= 2:
        out = out[1:-1].strip()
    return out


# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=("rules", "model"), default="rules")
    ap.add_argument("--backend", choices=tuple(ENDPOINTS), default="lmstudio")
    ap.add_argument("--model", default="qwen/qwen3.6-27b")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--src", type=Path, default=CORPUS,
                    help="JSONL to read; the model engine reads the rules output "
                         "when given one, so the two engines compose")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--only", default="", help="comma-separated series+number, e.g. body202,body26")
    ap.add_argument("--residue-only", action="store_true",
                    help="process only the entries the rules engine cannot finish. "
                         "Run this after a rules pass over --src: it keeps the other "
                         "entries deterministic and exposes ~17%% of the corpus to a model")
    ap.add_argument("--report", action="store_true", help="print the residue summary")
    ap.add_argument("--no-hand", action="store_true",
                    help="ignore corpus/modernised.tsv, to see what the rules alone do")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    subs, _ = load_lexicon()
    words = load_dict()
    hand = load_hand()
    hand_used = 0
    rows = [json.loads(l) for l in args.src.read_text(encoding="utf-8").splitlines()]

    if args.only:
        want = {s.strip() for s in args.only.split(",")}
        rows = [r for r in rows if f"{r['series']}{r['n']}" in want]
    if args.limit:
        rows = rows[:args.limit]

    unresolved: list[str] = []
    done = {}
    if args.engine == "model" and args.out.exists():
        for line in args.out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("modern"):
                done[(r["series"], r["n"])] = r["modern"]

    out_rows = []
    counts: dict[str, int] = {}
    failures = 0
    t0 = time.time()

    for i, r in enumerate(rows, 1):
        src = r.get("modern") or r["text"]
        if args.residue_only and not residue(src):
            out_rows.append(r)
            continue
        if args.engine == "rules":
            key = (r["series"], r["n"])
            if key in hand and not args.no_hand:
                r = dict(r, modern=hand.pop(key), engine="hand")
                hand_used += 1
            else:
                modern = modernise_rules(src, subs, words, unresolved)
                r = dict(r, modern=modern, engine="rules")
        else:
            key = (r["series"], r["n"])
            if key in done:
                r = dict(r, modern=done[key])
            else:
                try:
                    modern = call(ENDPOINTS[args.backend], args.model, src, args.timeout)
                    r = dict(r, modern=modern, engine=f"model:{args.model}")
                except (urllib.error.URLError, RuntimeError, KeyError, TimeoutError) as e:
                    failures += 1
                    print(f"  FAIL {r['series']}{r['n']}: {e}", file=sys.stderr)
                    r = dict(r, modern=None, engine=f"model:{args.model}")
                print(f"  {i}/{len(rows)} {r['series']}{r['n']} "
                      f"({time.time() - t0:.0f}s)", file=sys.stderr)
        for name in residue(r.get("modern") or r["text"]):
            counts[name] = counts.get(name, 0) + 1
        out_rows.append(r)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in out_rows) + "\n",
        encoding="utf-8")

    changed = sum(1 for r in out_rows if r.get("modern") and r["modern"] != r["text"])
    print(f"wrote    {len(out_rows)} entries -> {args.out}")
    print(f"changed  {changed}")
    if hand_used:
        print(f"by hand  {hand_used} from {HAND}")
    if hand and not args.no_hand and not args.only and not args.limit:
        # A hand rewrite for a number that is not in the corpus is a stale
        # transcription; saying so beats letting it sit unused, the same way
        # qa.py reports a redundant recovered.tsv line.
        left = ", ".join(f"{s}{n}" for s, n in sorted(hand, key=lambda k: (k[0], k[1])))
        print(f"unused   {len(hand)} lines in {HAND} match no entry: {left}")
    if failures:
        print(f"failed   {failures}")
    if unresolved:
        uniq = sorted(set(unresolved))
        print(f"unresolved -eth ({len(uniq)}): {', '.join(uniq)}")
        print("         no base verb in the dictionary — treat as OCR damage")
    if args.report:
        print("residue  entries the word-level engine cannot reach:")
        for name, n in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {name:16} {n}")
        touched = sum(1 for r in out_rows if residue(r.get("modern") or r["text"]))
        print(f"  {'ANY':16} {touched} of {len(out_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

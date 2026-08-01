# hadith — a `fortune` for hadith

A CLI that prints a saying of the Prophet, in the shape of `fortune`. The goal
is distribution through the normal channels: `apt install`, and from there the
other distros. That goal, not the code, is what drives most decisions here.

## The one constraint everything follows from

Debian's ftp-master checks `debian/copyright` for **every file in the package,
data as well as code**. A corpus licensed "personal, noncommercial use" fails —
not only for `main` but for `non-free` too, which still requires that Debian be
permitted to distribute it. And `non-free` is not enabled on most installs, so
shipping there would miss the point anyway.

So the corpus must be public domain or under a DFSG-free licence. This is a
build requirement, not caution.

### Precedent

`display-dhammapada` is in Debian main and ships a full scripture translation
as package data. Its `debian/copyright` is why it is allowed to: code
GPL-3.0+, and **every text file `License: public-domain`**.

An earlier version of this section described that package from memory and got
it wrong in three ways. All three were found by unpacking the actual `.deb`
(1.0-2, 2025-12-17), which is what this file's own conventions ask for:

- **It installs no fortune file at all.** It ships its own C binary and plain
  `.txt` files under `/usr/share/display-dhammapada/`; neither its `README` nor
  its `README.Debian` mentions `fortune` or `strfile`. The `.de`/`.m`/`.pl`
  multi-corpus shape this file used to cite as the model for our own layout is
  not in this version.
- **The quoted copyright stanza is not there.** `Muller` appears zero times in
  the real file. The translators credited are John Richards (1993), Ricardas
  Cepas (1997–2001) and Zbigniew Becker (2006).
- **So it does not work by age.** Those are living or recent translators who
  **dedicated** their work to the public domain. That is a different mechanism
  from an expired term.

None of which weakens our position, and that is worth being clear about:
Suhrawardy is public domain by age *independently*, and `bible-kjv` still
carries the age argument (the 1611 translation's rights have expired). What the
correction changes is only which precedent proves what. `display-dhammapada`
proves that Debian main accepts a scripture translation as package data on a
`public-domain` declaration; it proves nothing about *how* that declaration is
earned.

The layout question it no longer answers was settled against `fortunes-min`
instead — see *Distribution*.

## Source landscape (all verified, 2026-08)

### Modern online corpora, and why they are unusable here

Several complete hadith corpora are published online, and at least one has
good English coverage and no OCR problem at all. None of them can ship.

The pattern is the same everywhere: the terms permit **download and viewing
for personal, noncommercial use**, and require written permission for
republication or for any use by an organisation. That is enough for a
fetch-on-first-run tool and not enough for a package. Putting such a text in
an MIT- or GPL-licensed repository would be a licence misrepresentation —
granting rights we never held.

Shipping one would need an explicit grant, practically **CC BY 4.0 or CC BY-SA
4.0**. CC BY-**ND** would not do: a ban on derivatives is not DFSG-free, and
the modernisation pass is a derivative.

Two practical notes for anyone who tries again:

- **No public API.** Access means parsing server-rendered HTML, typically
  `?page=N` over chapter pages. Check `robots.txt` first; Cloudflare
  content-signal boilerplate neither grants nor withholds.
- **Strip the harakat before matching any Arabic word**, or the same word will
  not compare equal to itself.

The evaluation notes are in `hadith-reference-notes-2026-08-01.md`, outside
this repository.

### Other hadith sources, and why they are unusable here

- `fawazahmed0/hadith-api` — the repo is Unlicense, but that only covers the
  aggregator. Its `eng-bukhari` is **Muhsin Khan** and `eng-muslim` is **Abdul
  Hamid Siddiqui**: modern, copyrighted translations (protected in Germany into
  the 2040s and beyond). The text even carries sunnah.com's ﷺ glyph and
  sunnah.com appears in its `References.md`. *Nemo dat quod non habet* — the
  Unlicense file does not protect us. Still useful as an **Arabic** source and
  as a comparison reference; just never as shipped English.
- `sunnah.com` — now returns 403 behind Cloudflare. The API-key route is clean
  but binds us to their terms.
- `hadeethenc.com` — open API, ~65 languages including German, lowest practical
  risk, but formally still their copyright.
- Project Gutenberg has **no** hadith collections at all (verified: "hadith",
  "mishkat", "sayings of muhammad" all return 0 while the API works).

## Current corpus: Suhrawardy 1905

`The Sayings of Muhammad`, Abdullah al-Mamun al-Suhrawardy, 1905. 439 sayings,
alphabetically arranged over 85 topics. Public domain in the US (pre-1930) and
in Germany (author d. 1935, 70 years p.m.a. elapsed).

**The book numbers two series.** Its title page carries four sayings before the
first topic heading, numbered 1 to 4; the collection then restarts at 1 under
ABSTINENCE and runs to 439. Two number 1s, two number 4s. Deduping on the
number alone therefore swallowed the collection's first four sayings whole and
put the title page's four in their place — a silent misattribution that reached
the fortune file, since the reference line prints the number. `series` tells
them apart, and sitting under no topic is what identifies the preamble.

So "saying no. 1 is the same hadith as Bukhari no. 1" is true of the preamble's
first, not the collection's, which is *Remember the Lord in retirement from the
people*.

Source scan: `archive.org/details/the-sayings-of-muhammad_202401`. Note this is
a 1940s reprint — only the 1905 sayings body is free, **not** the later preface
and introduction, which the parser therefore excludes.

Second candidate, not yet processed: Lane-Poole, *The Speeches & Table-Talk of
the Prophet Mohammad* (1882), `archive.org/details/speechestabletal00lane`,
flagged there as `NOT_IN_COPYRIGHT`.

### The scan's traps

Each of these cost a debugging round; they are why the parser looks the way it
does.

1. **The opening pages are scanned three times.** Parsing from the first
   occurrence of the body marker yields four sayings and then front matter.
   Take the *last* occurrence.
2. **Footnotes and back matter bleed into entries.** Line-based parsing let
   saying 439 swallow the entire glossary — 7106 characters. Blocks separated
   by blank lines are the right unit: a footnote is its own block and can be
   dropped whole. Entry numbers always carry `.` or `,`; footnote markers are
   bare digits. That is the discriminator.
3. **Block boundaries do not match logical ones.** A heading and the saying
   after it often share a block, and several short sayings run together with no
   blank line. So every *line* must be classified, not just `block[0]`.
4. **Sayings can start mid-line.** Where a page break fell inside a paragraph
   the OCR emits `...the right path. 241.' The greatest enemies...`. Saying 240
   silently contained 241 — a misattribution, which in a hadith corpus is not
   cosmetic. `split_inline()` only splits when the number found is exactly the
   successor, so ordinary numerals cannot trigger it.
5. **One speck of ink costs a whole topic.** The heading pattern is anchored at
   the end of the line, so `Of THE DEAD '` and `OfDEATH »` both failed to match
   and every saying beneath them was filed under the previous topic. A heading
   always ends on a letter, so anything else there is debris — matching that
   generously took the topic count from 79 to the 85 the book actually has.
6. **The running head announces the next topic.** Each page repeats the section
   name at the top, and where a new section starts partway down a page that
   running head names it *before* the section heading does — so the sayings in
   between are filed one topic early. Saying 102 sits in exactly that gap.

   Position cannot separate the two, and this is the part worth remembering: a
   running head usually *precedes* the heading it duplicates, but where a
   section heading falls at the foot of a page the next page's running head
   repeats it *afterwards*. A rule keyed on order gets one of the two cases
   backwards, which is how saying 61 ended up under Cleanliness instead of
   Compassion.

   Typography does separate them. The section heading sets `Of` in italic mixed
   case, the running head sets `OF` in full capitals, and the OCR preserves
   that. So the running heads are dropped as page furniture before parsing, and
   the heading pattern can then be generous about what it accepts for the
   italic `f` — which the scan renders as `Of`, `OP`, `Oy`, `Ol`, `OQ)` and
   once as a lower-case `of`.
7. **Two headings are damaged past any pattern.** `Of wIpows` fails the
   upper-case test and `Of HUMIL.` is simply cut short. Both are corpus data,
   so they are repaired from `corrections.tsv`, which the parser now also
   applies to heading lines rather than keeping a second table of its own.

### The OCR errors are systematic

Two defects account for most of them, which is why a curated table works:

- the acute accent of the transliteration reads as `i`: `Rasil` → Rasúl,
  `Islim` → Islám, `Kur'in` → Kur'án, `Imin` → Imán
- e/c confusion: `docth` → doeth, `cach` → each, `seck` → seek,
  `cunuch` → eunuch

Only corrections with exactly one plausible reading go in `corrections.tsv`.
Anything ambiguous stays out deliberately, so `qa.py` keeps reporting it.

### State

```
439  sayings in the collection, plus 4 in the preamble
439  present                   (100 %, of which 25 transcribed from the scans)
443  clean, written to the fortune file
  0  flagged, held back
  0  unreviewed debris         (8 flagged, opened at the page, correct as printed)
 71  anchored repairs in artefacts.tsv, every one checked against the image
```

Median 183 characters — the format genuinely suits `fortune`.

**An earlier version of this section claimed the same clean state and was
wrong**, which is the part worth keeping. The claim rested on `qa.py` reporting
no unaccounted-for token and on an artefact sweep run once by hand. Both were
looking in the wrong place:

- **`qa.py` waved through anything ending in `-eth` or `-est`** without a
  dictionary check, on the reasoning that archaic verb forms are not in the
  wordlist. Any OCR damage that happened to end in `-eth` was therefore
  invisible by construction. `secketh` (202, 278), `sceth` (178) and `cateth`
  (189) all sat in the corpus for that reason — all three the same e/c
  confusion `corrections.tsv` was written for. It now derives a base verb and
  accepts the form only if one exists.
- **A token check cannot see debris that is not a token.** A footnote marker, a
  running head, half of the next saying, a bare `&` — none is a word, so
  nothing looked at them. The sweep now in `qa.py` found 58 entries.

Both are fixed and all 443 entries ship. What the 58 turned out to be:

- **Two were misattributions**, the same defect as trap 4 above: a saying whose
  number the OCR destroyed, so `split_inline()` never saw the boundary and the
  previous saying swallowed it. Saying **4** carried the whole of saying 5
  (its number read as `$-`), and saying **100** carried saying 101 (`101.` read
  as `tor.`). Both of the swallowed sayings were already in `recovered.tsv`, so
  the corpus counted as complete while the duplicate went on being printed
  under the wrong number. **Recovering a saying and leaving its wreckage in the
  predecessor is the failure mode to watch for** — the recovery is what hides
  it.
- **Two were the opposite of debris: lost text.** Saying **224** ended at
  `the thongs of your sandals;` and **356** at `nor a violent`. The djvu pass
  had dropped `and the Fire likewise.` and `speaker.` The ABBYY pass has both,
  and the page confirms both. A sweep written to find *extra* characters is
  what turned up two entries missing them, because the tell in each case was
  the same: the entry did not end on a full stop.
- The rest were footnote markers, running heads (355 had swallowed the heading
  of the section *following* it), specks of ink read as `|`, `&`, `\` or a
  stray letter, and 24 full stops the OCR read as commas.

Reading every affected page then turned up two further classes that the sweep
had no way to see:

- **Both readings are real English words.** Saying **416** read *"Wives have
  got the upper hand of their husbands from **beating** this"*; the page prints
  **hearing**. Nothing short of the image finds that.
- **A speck before a lower-case word reads as an opening quote** — `his 'own
  labour`, `Every 'nan who shall beg`, `Adam, 'one of them death`. Six of them.
  This one *is* mechanical and is now a rule: the transliterations do begin
  with an apostrophe — `'A'ishah`, `'Uthmán` — but they are capitalised, so a
  lower-case word after one is debris.

`cateth` is the one no automatic check can find: it derives to `cats`, a real
word, so both the dictionary check and the `-eth` derivation accept it. The
same is true of `what you cat yourself` in 389 and 414 — and saying 32 is
about an actual cat, so even the correction has to be anchored. All three were
found by reading the modernised output, which is the argument for the
modernisation pass being a proofreading instrument and not only a register
change.

**Two OCR passes agreeing was not treated as sufficient.** All 41 affected
pages were rendered from the archive.org PDF and read. That is what settled
224 and 356, and it is what leaves saying **171** honest: djvu reads
`religion,`, ABBYY reads `religiory`, and the page prints a mark with a
descender that is either a comma or a full stop that has taken ink from the `n`
above it. It is set as a full stop because every other saying in the book ends
on one and the sentence is complete — but that is a judgement, and
`artefacts.tsv` says so on the line.

85 topics, against the 79 an earlier parse reported — see the two heading traps
below.

The 25 that the OCR had lost are in `corpus/recovered.tsv`, read off the page
images. In every case the entry *number* was what the OCR destroyed — `21.` came
through as `a1.`, `51.` as `Ji.`, `52.` as `$2.`, `101.` as `tor.` — and with
no number to key on, the parser dropped the text with it. That is why they were
missing rather than merely garbled, and why no correction table could have
recovered them.

The 50 entries the OCR damaged past word-level repair are in
`corpus/proofed.tsv`, transcribed whole from the images. What made them
unfixable by table was that the OCR had merged *foreign material* into the
saying — a footnote, a running head, a page number, or the next entry — and
often truncated it at a page break as well, so the text had to be assembled
from two pages.

(An earlier note here had the 25 missing sayings *hanging off their
predecessor*. They were not: the parser had discarded them outright, which is
why reading the predecessors turned up nothing.)

### The second OCR pass finds what the first destroyed

The archive.org item carries the book twice: the djvu text the parser reads,
and a pass by ABBYY FineReader 14 inside the PDF. They fail in *different*
places, which is what makes the pair worth more than either alone — the djvu
has 414 of 439 entries, ABBYY 419, and the two sets do not nest.

```
tools/abbyy_diff.py     aligns the two passes, reports what the other read
```

It cut the 40 flagged entries to 18 in one pass. But **agreement between two
OCR passes is evidence, not proof**, and disagreement does not mean the
cleaner-looking pass is right:

- saying 318 is `for her to sit upon`; ABBYY reads `hereto`, which is a real
  word and survives any dictionary check. Only the page image settles it.
- saying 291 is `noble`; the djvu reads `goble` and ABBYY `jioble`. Both wrong,
  and the right answer is in neither.

So the tool proposes and the image decides. Every entry acted on was opened.

### The flags have to be taken again after the corrections

Damage detection ran once, on the raw parse. Since corrections and proofreading
are precisely what remove the characters the rules look for, the flags went
stale and held back 17 entries that were by then clean. `qa.py` now recomputes
them at the end.

Two of the rules were also worth more than they were catching:

- **`non-ascii` fired on every accent.** `Rasúl` and the em dash are put there
  on purpose by `corrections.tsv` and `clean()`, so flagging all non-ASCII made
  the flag meaningless. It now allows the acute-accented set and the dash.
- **A bare digit is nearly always damage** — the mangled number of the next
  saying, or a footnote marker. The sayings spell their numbers out; the sole
  real use is the parenthesised enumeration in saying 185. That rule found 15
  entries that no other check saw, and an unbalanced-quote rule found 10 more.
  Both classes were invisible until looked for, which is the argument for
  sweeping for artefacts rather than trusting a clean flag count.

### A divergence to settle before shipping

The printed book uses **macrons** — `Jihād`, `Imān`, `'Ā'ishah` — where
`corrections.tsv` normalises to the acute, `Jihád`. That is an established
choice in this corpus and it is applied consistently, but it is a divergence
from the source and should be a deliberate decision, not an inherited one.

One entry is also a genuine oddity rather than an error: the book prints
**two sayings both numbered 336**, `336. (i)` and `336 (ii)`. They are kept in
a single record, since the book gives them a single number and dropping either
would lose a saying.

## Modernising the English

Settled 2026-08-01: **the Victorian English does not ship.** `payeth`, `thou`
and `verily` are what a reader meets first, and they make a living text read as
a museum piece. The 1905 wording is the semantic work of a human translator and
stays in the JSONL beside the result, so every change is a diff — which is the
whole reason this is defensible where a fresh translation from Arabic is not.
The modernisation is our own work and can carry CC0.

231 of the 443 entries — 52 % — carried at least one archaism: 255 `-eth` verbs
in 135 distinct forms, 107 `thou`/`thee`/`thy`/`ye`, 107 `hath`/`doth`/`saith`,
69 `verily`.

### The problem has two halves and they need different tools

**Morphology is deterministic and the machine should own it.** `corpus/
modern-lexicon.tsv` carries the pronouns, auxiliaries and adverbs; the 135
`-eth` verbs are *not* in it, because listing them by hand would have hidden
the ones that are OCR damage rather than archaism. They are derived against the
system dictionary instead, and it gets 131 of 135 right on its own.

The derivation is worth stating, because the obvious rule fails: drop `eth`,
add `s` gives `coms` and `knowes`. Victorian spelling drops the silent `e`, so
the stem is ambiguous and the dictionary has to pick the base — and the order
of candidates decides it. `care` must be tried before `car`, or `careth`
becomes `cars`.

Four cases beat it, and all four are in the lexicon:

- `putteth` → `putts` and `aideth` → `aides`, because `putt` and `aide` are
  real words and the dictionary cannot break the tie
- `teeth` is not a verb at all
- `sceth` → `scs`, because `sc` is in the Debian wordlist. Any base with no
  vowel is not a word however firmly the wordlist says otherwise, and that
  guard is what makes the OCR damage visible again

**Syntax is not deterministic and the machine must not own it.** No word-level
pass turns `Kill not your hearts` into `Do not kill your hearts`, and where one
tries it makes things worse: `Solve Thou my difficulties` becomes `Solve You my
difficulties`, which is worse English than the 1905 line. So the rules engine
reports its own residue — the entries it provably cannot finish — and those
are answered in `corpus/modernised.tsv`, keyed like `proofed.tsv`.

```
443  entries
256  changed, of which 64 are hand-written rewrites in modernised.tsv
 34  still reported as residue, all of them false positives on re-reading
  1  archaism left in the whole corpus, and it is the noun `teeth`
```

Eleven entries were held out of `modernised.tsv` at first because the OCR had
damaged them and a rewrite would have baked the damage in. That is the rule to
keep — **repair first, modernise second** — even though the list is now empty.

The residue patterns are deliberately generous: a false positive costs a
reading, a false negative ships. But generous is not the same as sloppy, and
one of them was quietly wrong. The negative-imperative rule excluded `not the`
— written to spare *"not the only"*, it instead spared every negative
imperative that has an object, which is most of them. `Fear not the obloquy of
the detractor` sat unflagged behind it. What has to be excluded is the **verb**
(`do not`, `must not` are already modern), not the object. Correcting that
dropped the false positives from 28 to 0 and turned up the one real case.

### What the check is for

`modernise_check.py` compares old against new mechanically — proper names,
numerals, content words after the lexicon is accounted for, length ratio,
quotation marks, leftover archaisms. It exists for the model engine, not the
rules engine: a model asked to change the register will sometimes change the
claim as well, and a fluent sentence hides that completely. It flags every
hand-written rewrite too, by design — a rewrite *is* a content change, and the
flag is what makes someone read it. That is how `body329` was caught turning
`in the Here and the Hereafter` into `in this world and the next`, which is a
theological term traded for a paraphrase.

### What the model engine is worth, measured

`qwen3:32b` was run over the same 74 residue entries as an independent pass:
62 minutes, 73 of 74 answered, one timeout. Median similarity to the
hand-written version 0.67, so the two agree on substance and differ on wording
almost everywhere — which is what makes the disagreements informative:

- It made **the same error on 329**, `the Here and the Hereafter` → `this life
  and the next`. Two independent passes reaching for the same paraphrase is the
  argument for the check being mechanical rather than a matter of who wrote it.
- It drifts on exactly the loaded terms, the same failure the translation pilot
  found: `discharge your trust` → `fulfill your responsibilities` (that is
  *amānah*), `If Thou art not displeased` → `if You are not angry`, `assisting
  a man upon his beast` → `helping someone with their animal`.
- It **quietly switched orthography.** Suhrawardy spells British throughout —
  `splendour`, `honoureth`, `labour` — and qwen introduced `fulfill`, `rumors`,
  `travelers`, `recognize`, `favor`. No content check would ever see that, so
  `modernise_check.py` now diffs against the British/American wordlists. The
  shipped corpus introduces none.

So the model engine is a proposal engine. It is the right tool for the next
corpus — Lane-Poole is 1882 and will have the same residue — but what it
produces is a draft to be read, not an answer.

### The pass is also a proofreading instrument

Modernising 443 sayings means looking at every verb in the corpus, and that is
how `cateth`, `secketh` and `sceth` surfaced after `qa.py` had reported the
corpus clean — see *State* above. Expect the same of the Lane-Poole corpus when
it is processed.

### The eulogy

Settled 2026-08-01: **the Prophet always carries `(saw)`**, by name and by
epithet. 598 occurrences across the file — 443 of them the reference line,
which prints the book's title on every entry.

It is added in `make_fortune.py`, at render time, and in **neither** corpus.
That separation is the point: the 1905 JSONL is a faithful reproduction of a
public-domain book and is what the licence claim rests on, and the modernised
JSONL is meant to diff cleanly against it. An eulogy is neither a reading nor a
register change — it is how the name is set — so it belongs to the rendering,
where it reaches both output files without touching either source.
`--no-eulogy` turns it off.

Three details that are decisions rather than defaults:

- **Glued, not spaced.** `Muhammad(saw)`, for the same reason the German
  edition sets it as a superscript: `textwrap` breaks at spaces, and a line
  beginning with a bare `(saw)` has separated the eulogy from the name. Glued,
  it is one token and cannot come apart.
- **The possessive takes it after the `'s`** — `Muhammad's(saw)` — as the
  modern English editions set it.
- **The whole reference line, not just the attribution.** Eleven of the book's
  section headings are named after him (`Muhammad The Prophet's Kindness`), and
  eulogising only the title left those bare.

The guard against a doubled `(saw)` on re-rendering is worth spelling out
because it defeated itself once. `\bMuhammad(?:'s)?\b(?!\(saw\))` looks
sufficient and is not: against `Muhammad's(saw)` it tries the possessive, fails
the lookahead, then **backtracks to the bare name**, where the next characters
are `'s(saw)` rather than `(saw)` — so the guard passes and the name is
eulogised twice. The lookahead has to exclude both forms.

**The epithets carry it too**, which took a second pattern rather than a
longer alternation, because three things had to be got right:

- **`of God` is part of the title**, so the eulogy goes after the whole phrase:
  `the Messenger of God(saw)`, not `the Messenger(saw) of God`.
- **Where the epithet is immediately glossed with the name, only one eulogy
  belongs there** — `the Rasúl (Muhammad(saw))`, not both.
- **Saying 134 is about other prophets.** *"There was not any Messenger sent
  before me by God to mankind"* — they take `(as)`, never `(saw)`. It is the
  one place in the corpus where the same word means someone else, and
  eulogising it would be a doctrinal error rather than a typographic one.
  `any Messenger` is excluded; the plurals (`the other messengers of God`,
  `inferior to the prophets`) are kept out by a word boundary.

`messenger` is matched in lower case as well, because saying 57 has the Prophet
call himself *"the servant of God, and His messenger"* and 199 has *"God and
His messenger"*. 598 eulogies in all.

### Two fortune files

```
fortune/hadith-suhrawardy        the modern text — this is what ships
fortune/hadith-suhrawardy-1905   the original, kept so the diff stays public
```

Costs nothing, and `display-dhammapada` already establishes the multi-file
shape. `debian/copyright` then reads cleanly: the 1905 text public-domain, the
modernisation ours under CC0.

## Pipeline

```
tools/parse_suhrawardy.py   raw OCR   -> corpus/suhrawardy-1905.jsonl
tools/qa.py                 merges recovered.tsv, applies corrections.tsv and
                            artefacts.tsv, flags what needs a human, sweeps
                            for debris
tools/modernise.py          1905 text -> corpus/suhrawardy-modern.jsonl
tools/modernise_check.py    does the modern text still say the same thing
tools/make_fortune.py       jsonl     -> fortune/hadith-suhrawardy
tools/build-deb.sh          the tree  -> hadith_<version>_all.deb, out of tree
tools/release.sh            the tree  -> a signed GitHub release, from a
                            workstation only — see *Releases on GitHub*
```

Run in that order. The first four are needed only to *change* the corpus: the
JSONL they produce is committed, so `build-deb.sh` on a fresh clone works on
its own, and `debian/rules` calls only `make_fortune.py`. `qa.py` rewrites the JSONL in place, so `parse` must precede
it, and `modernise.py` reads what `qa.py` wrote. `make_fortune.py` holds back
flagged entries by default — `--include-flagged` to see them while
proofreading — and takes the modern text where there is one, falling back per
entry to the 1905 text, so a partial pass still produces a complete file.

`corpus/known-words.txt` is the allowlist of proper nouns and archaic English
that the system dictionaries lack, so that `qa.py` reports only real damage.

Three data files carry what the scan could not give up, all keyed by number and
all recording the scan page so a reader can check them:

- `corpus/recovered.tsv` — sayings the OCR lost outright. `qa.py` merges them
  but never lets one displace a parsed entry: if a number starts parsing on its
  own, the recovered line is reported as redundant instead of silently
  overwriting, so that a stale transcription cannot outlive the defect it
  worked around.
- `corpus/proofed.tsv` — entries whose text was replaced by the transcription.
  Here overriding *is* the point, so it does override. It lands after the
  corrections, so no substitution can reach into proofread text, and before the
  unknown-token check, so the transcription is held to the same standard as
  everything else. A leading `P` in the number column addresses the preamble
  series.

- `corpus/artefacts.tsv` — debris the OCR pulled into an entry, and the single
  anchored edit that removes it. This is the third repair layer, and it exists
  because the other two do not fit: `corrections.tsv` substitutes whole words
  and most of this damage is punctuation or page furniture, while retyping a
  600-character entry into `proofed.tsv` to delete one asterisk adds more risk
  than it removes.

  The guarantee is that `find` must occur in the entry **exactly once**. Zero
  matches means the repair is stale and is reported the way a redundant
  `recovered.tsv` line is; more than one means it is ambiguous and would be a
  guess. Neither is applied. A line may also read `OK`, which records that the
  entry was flagged, opened at the page, and is right as printed — that is what
  keeps the sweep reporting the unreviewed rather than the merely flagged.

  It lands *after* `corrections.tsv`, so that the anchors can be written
  against the text a reviewer actually reads: anchoring `Islám?"'` on the raw
  parse would have meant writing `Islim?"'`.

Two more carry the modernisation, on the same convention:

- `corpus/modernised.tsv` — the hand-written rewrites, overriding the rules
  engine for the entries where a word-level pass is not enough. The entries
  deliberately absent are listed in a comment at the foot of the file with the
  reason, so that a gap is a decision on the record rather than an omission.
- `corpus/modern-lexicon.tsv` — the word-level substitutions themselves.

`strfile` is **not installed** here; it lives in `fortune-mod`.

## On translating from Arabic

Considered and deferred. A fresh translation would be legally ideal — our own
copyright, licensable CC0, straight into `main`. Three things argue against it
as the near-term path:

- Hadith translation is a scholarly discipline with technical terms and settled
  conventions. The machine failure mode is *plausible and wrong*, which is
  exactly what survives proofreading.
- It ships via `apt` under the line "-- Sayings of Muhammad". A subtly wrong
  rendering then gets quoted as a prophetic saying.
- No named human stands behind it. Every established translation carries a name
  that answers for it; "generated by a language model" is not a chain of
  authority.

The tone problem is better solved a step lower: **modernising Suhrawardy's
Victorian English is a register change, not a meaning transfer.** The semantic
work was done by a human in 1905, the original sits next to the result, and
every substantive divergence shows up in a diff. The 1905 text being public
domain, the modernisation is our own work and can carry CC0.

That is now done rather than proposed — see *Modernising the English* above.

### If a local model is wanted anyway

Verified on HuggingFace, all **Apache-2.0** (so no NC clause to reintroduce the
licensing problem — unlike Cohere's Aya / Command-R, which are CC-BY-NC):

| Model | Size | Note |
|---|---|---|
| `QCRI/Fanar-1-9B-Instruct` | 9B | card states alignment with Islamic values; GGUF builds exist |
| `QCRI/Fanar-2-27B-Instruct` | 27B | |
| `inceptionai/Jais-2-8B-Chat` | 8B | Arabic–English bilingual |
| `inceptionai/Jais-2-70B-Chat` | 70B | |

This solves the licence question, not the quality one. A 9B model is weaker at
classical Arabic than a frontier model, not stronger.

## Validating a translation against existing ones

Sound as a method, with three caveats found by testing:

- **Hadith numbers do work as keys** across sources. Two independent online
  corpora lined up exactly over a sampled run (99, 100–104, 106, 107 in order).
  Carry the numbering scheme along, though — sunnah.com displays several in
  parallel for a reason.
- **Do not join on text prefixes.** Different ahadith share identical isnāds
  (`حدثنا عبد الله بن يوسف قال حدثني الليث…`), which produced two false matches
  in ten. Join on the *matn*, or on the number.
- **Suhrawardy has no references at all** — 0 of 414 entries cite a source. So
  this method cannot be applied to that corpus; the join would first have to be
  established by fuzzy content search, checking an uncertain translation
  against an uncertain mapping.

Agreement is not proof: two translations from one interpretive tradition are
not independent witnesses, and divergence may be legitimate variance. The
method yields **triage, not a verdict** — it says where a human must look.

Licence hygiene: reading Muhsin Khan as a *reference* is fine, that is not
reproduction. Revising *toward* it on divergence would drift into a derivative
work. Divergence gets flagged, a human decides, phrasing is never adopted.

## The translation pilot, and why the project does not translate

A pilot ran 42 ahadith through five models to test whether translating from
the Arabic was a viable path. **Removed from the repository 2026-08-01**,
along with the notes on the reference translations it was checked against,
so that the public repository does not name a particular community. Nothing
in it was load-bearing for the shipped package — the corpus is Suhrawardy
1905, which is public domain and unaffiliated.

```
hadith-pilot-backup-2026-08-01.tar.gz     the scripts and every run output
hadith-reference-notes-2026-08-01.md      the source evaluation notes
```

Both sit in the directory *above* this repository, deliberately outside it.

Four findings survive it, and they are the reason *On translating from Arabic*
concludes as it does:

- **Embeddings do not verify a translation.** Matching each Arabic hadith to
  its translation by nearest neighbour got 38/42 into English and 32/42 into
  French and Turkish, at margins of about 0.04 inside a 0.54-0.69 band. The
  obvious hypothesis — that the shared isnad formula dominates the vector — is
  wrong: stripping it made matching slightly *worse*. It is a cross-script
  weakness. At those margins the check would raise about 10 % false alarms and
  still miss real errors, so a content check has to be a semantic judgement and
  not a vector distance.
- **Models agree on the routine and part on rare lexis.** On a phrase meaning
  *visit at intervals*, the two frontier models were right and all three local
  models read the word as though it were a different one entirely. A 27B model
  was no better than a 9B here, so this is not something size fixes.
- **Inter-model disagreement is a working check.** Minimum pairwise similarity
  across runs, with the boilerplate stripped, below about 0.45. Over five
  models it caught both real errors — and an unterminated reasoning block in
  the harness, so it surfaces pipeline defects and not only translation ones.
  It costs nothing and needs no reference text.
- **A hard case is worth checking for a data defect first.** One item looked
  contested across every model and was not: the scrape feeding it had paired
  one hadith's Arabic with another's translation, and a second had no
  translation at all, only a citation line. The disagreement was the data, not
  the models.

Two traps in running the models locally, kept because they will recur:

- **Reasoning models spend the token budget before answering.** One returned
  its chain in `reasoning_content` and left `content` empty, producing 0 of 42.
  Another sometimes opened a `<think>` block and never closed it, so 16 671
  characters of raw reasoning arrived looking like an answer. Raise on an
  unterminated block rather than passing it on.
- **Pull the Instruct variant.** The base model will not follow instructions,
  and the GGUF repository names differ by one word.

VRAM is the binding constraint: two 16 GB cards, and a 32B model at Q4 fills
both. Unload before starting another run. A model pull running concurrently
starves model *loading*, which shows up as a 28 %/72 % CPU/GPU split and
roughly a tenfold slowdown.
## Distribution

Debian needs an ITP bug and a sponsor via `mentors.debian.net`; realistically
months. Ubuntu PPA, AUR and openSUSE OBS are days.

**The directory is `fortunes`, plural.** This file said `fortune` throughout
until 2026-08-01, and a package installing there would have been invisible to
`fortune` — nothing would have errored, the sayings simply would never have
come up. Verified against the paths compiled into `/usr/games/fortune` and
against what `fortunes-min` actually installs.

Ship multi-corpus from the start, which is what `fortunes-min` does with
`fortunes`/`literature`/`riddles`:

```
/usr/share/games/fortunes/hadith-suhrawardy
/usr/share/games/fortunes/hadith-lanepoole
```

Each cookie file also needs its `strfile`-generated `.dat` beside it, and by
archive convention a `.u8` symlink back to itself.

Then a later licence grant is a data add-on, not a rebuild. A maintained
package already in Debian is also a far better argument in a permission request
than an intention.

Whatever the code licence, add a separate `DATA-LICENSE.md` stating the corpus
terms per file. Five lines, and it takes the sting out of the whole question.
Done — it is in the repository root and is installed into
`/usr/share/doc/hadith/`.

### The package, as built 2026-08-01

Source `hadith` 0.1.0-1, format `3.0 (quilt)`, debhelper compat 13,
Standards-Version 4.7.3, two binary packages both `Architecture: all`.

```
hadith            24 KB   Depends: fortune-mod, fortunes-hadith (= ${source:Version})
  /usr/games/hadith                                      wrapper, POSIX sh
  /usr/share/man/man6/hadith.6.gz
  /usr/share/doc/hadith/{copyright,README.md,README.Debian,changelog}

fortunes-hadith  226 KB   Recommends: fortune-mod
  /usr/share/games/fortunes/hadith-suhrawardy{,.dat,.u8}   modern, the default
  /usr/share/games/fortunes/hadith-suhrawardy-1905{,...}   the 1905 text
  /usr/share/doc/fortunes-hadith/{copyright,DATA-LICENSE.md,changelog}
```

**The split is what the naming question turned on.** `fortune-hadith` looks
like the obvious name and is the wrong one, for a reason that only shows up in
the archive: of the 23 packages whose name begins `fortune`, 22 are
`fortunes-*` and one is `fortune-anarchism` — and **all 23 are data-only**.
`fortunes-min` and `fortune-anarchism` were unpacked to confirm it; neither
puts anything in `PATH`. So the prefix is a promise, and a package shipping
`/usr/games/hadith` under it would break that promise.

Debian's own answer for scripture is `bible-kjv` (the command) plus
`bible-kjv-text` (the text) out of one source, and that is what this now does.
`fortunes-hadith` is then a plain data package like all the others, and
`hadith` is a command that depends on it. The data package uses
**`Recommends: fortune-mod`, not `Depends`** — that is what `fortunes-min` and
`fortune-anarchism` do.

Naming the source package `hadith` rather than `fortunes-hadith` keeps the
repository name, the source name and the command name identical, which is worth
more than matching the data package's prefix.

Section 6 and `/usr/games`, because Policy 11.11 puts games there; it is in
Debian's and Ubuntu's default `PATH` via `/etc/environment`.

Four things that are decisions rather than defaults:

- **The cookie files are built from `corpus/*.jsonl`, not shipped ready-made.**
  Verified first that both regenerate bit-identically from the JSONL, so
  nothing is lost by leaving them out. `fortune/` is therefore a build product,
  is gitignored, and `debian/rules clean` deletes it. It must also stay out of
  the orig tarball: `3.0 (quilt)` cannot represent the deletion of a file that
  came out of it, so a build would fail at the very end.
- **`Architecture: all` is safe even though the `.dat` is binary.** `strfile`
  writes its offsets through `htonl`, so the index is big-endian whatever built
  it. Do not pass `strfile -r`, which randomises the offset table and would
  destroy reproducibility. Two consecutive builds currently produce a
  bit-identical `.deb`.
- **`strfile` is called without `-s`.** Its summary puts the entry count in the
  build log, which is the one place a truncated corpus would announce itself.
- **The build runs out of tree**, via `tools/build-deb.sh`, because
  `dpkg-buildpackage` wants a directory named `hadith-<version>` and the
  working tree is not that. A build never touches the tree being edited.

Lintian is clean except for two tags that cannot be resolved yet:

```
W: initial-upload-closes-no-bugs    needs the ITP bug number
P: no-homepage-field                fixed — Homepage now set
```

**Run lintian with `--profile debian`.** Ubuntu's profile reports
`E: bad-distribution-in-changes-file unstable`, which is correct for Ubuntu and
wrong for us: the package targets Debian, and `unstable` is right in
`debian/changelog`.

One consequence worth knowing before anyone reports it as a bug: installing
`fortunes-hadith` makes plain `fortune` draw from the hadith corpora about half
the time, because fortune weights by **file size** and the two files together
are larger than `fortunes`, `literature` and `riddles` combined. Nothing is
wrong; that is how fortune apportions. The only lever is to install one corpus
rather than two.

No `Breaks`/`Replaces` between the two packages is needed, because the
single-package 0.1.0-1 was never released — the split happened before the first
upload. If a version of `hadith` owning the cookie files ever *does* reach an
archive, `fortunes-hadith` will need both against it, or the upgrade will fail
on a file conflict.

### Releases on GitHub, and what a signature is worth here

Set up 2026-08-01. The Debian route is months; a release is what lets someone
install today, and — the part that actually pays — it is what gives the source
package a public upstream tarball to point at.

**Signing the `.deb` itself would be theatre.** `/etc/dpkg/dpkg.cfg` ships
`no-debsig`, with the comment *"since the distribution is not using embedded
signatures, debsig-verify would reject all packages"*, and `debsig-verify` is
not installed. Nothing on a Debian or Ubuntu system ever checks such a
signature. So the signatures are detached, over `SHA256SUMS` and over the
tarball, and are checked by hand or by `uscan`.

**The orig tarball was the real gap.** `3.0 (quilt)` splits a source package
into an upstream tarball and the packaging, so that a third party can fetch the
former independently and hold it against the checksum in the `.dsc`. That was
impossible: `build-deb.sh` invented the tarball from the working tree, and it
existed nowhere else. A release asset plus `debian/watch` plus
`debian/upstream/signing-key.asc` closes it — `uscan --verify` now answers the
question a sponsor would otherwise have to take on trust.

**The asset is ours, not GitHub's generated tag tarball.** The measured
difference between the two is exactly `debian/` and nothing else — `fortune/`,
`reference/` and `corpus/raw` are gitignored, so `git archive` never had them
either, and an earlier note here that claimed otherwise was wrong. A `debian/`
inside the orig tarball would in fact be harmless, since `dpkg-source(1)`
removes any pre-existing one before applying the debian tarball, and no lintian
tag objects. So the generated tarball was rejected on the other two grounds:
GitHub produces it, so it cannot carry our signature, and its bytes are
GitHub's to change.

**The key does not go into a GitHub secret.** It is the Debian upload key —
`dpkg-buildpackage` selects it by the address in `debian/changelog` — so a
compromise of the repository would be a compromise of the Debian identity.
`tools/release.sh` therefore runs on a workstation and CI never signs anything.
It defaults to a dry run; `--publish` is what tags, pushes and publishes.

That decision costs something, and the cost is where the interesting part is.
Since `debian/upstream/signing-key.asc` is now in the packaging, lintian wants
an `.asc` beside every orig tarball it sees:

```
W: hadith source: orig-tarball-missing-upstream-signature
```

and the CI runs `--fail-on error,warning`. The ordinary CI build has no key and
structurally cannot satisfy that, so it suppresses the tag. **A suppression is
how this project's worst bugs survived**, so it does not stand alone: a
`verify-release` job fires on `release: published` and does what a sponsor
does, with no private key —

- `gpgv` against a keyring built from `debian/upstream/signing-key.asc`, not
  from the runner's keyring, because that file is what a sponsor's uscan will
  trust
- unpacks the published tarball and the freshly built one and `diff -r`s them,
  so the release provably contains the tagged commit. Compared **unpacked**:
  the tar stream is deterministic, but the gzip wrapping it is not guaranteed
  to be byte-stable across versions, and a mismatch there would be a false
  alarm about the one thing that matters, the content.
- rebuilds from the published tarball plus `debian/` — and runs lintian
  **without** the suppression, since there the signature does exist
- runs `uscan --download-current-version`, and asserts the `.asc` landed.
  uscan exits 1 on no match, but a watch file that downloads and silently
  skips verification has the same exit code.

`version=4` in `debian/watch`, not 5. devscripts 2.26 understands 5, but the
lintian on an Ubuntu runner knows only 2, 3 and 4 and would report the file as
an unknown standard.

**The releases page has no assets in it.** The first watch file pointed at
`https://github.com/…/releases` and matched hrefs, which is the shape every
GitHub watch-file example uses, and it found nothing. uscan says *"no matching
hrefs"*, which reads as a wrong pattern and is not: that page carries no asset
link at all, because GitHub fetches the list afterwards from
`/releases/expanded_assets/<tag>`. Grepping both settles it — zero download
links in the first, all six in the second — so no href pattern over `/releases`
can ever match, however it is written. The source is therefore
`api.github.com/repos/…/releases` with `searchmode=plain`, which matches
against the whole JSON body instead of hunting for hrefs.

That one is the argument for the `verify-release` job existing at all. The
watch file parsed, `uscan --no-download` exited 0, and the expanded pattern
looked right in the log. Only running uscan against a real release found it,
which is why the CI step asserts the downloaded `.asc` rather than trusting the
exit code.

Two things that will bite whoever touches this next:

- **The tag carries the upstream version, not the Debian revision** — `v0.1.0`,
  never `v0.1.0-1`. uscan tracks upstream. A Debian-only change (`0.1.0-2`)
  reuses the published tarball and needs no release at all, which is why
  `release.sh` refuses an existing tag rather than clobbering it.
- **The repository is `fortune-hadith` and the source package is `hadith`.**
  `@PACKAGE@` expands to the latter, so it is right for the asset filename and
  wrong for the URL path. uscan's directory-name check was tested against a
  checkout named `fortune-hadith` and does not object, so no
  `--check-dirname-level` is needed.

## Conventions

- Verify claims about sources, licences and package policy against the actual
  artefact — `debian/copyright`, `robots.txt`, the API response — rather than
  from memory. Every correction in this file came from doing that.
- Corrections to the corpus are data, not code: they belong in
  `corrections.tsv` with a comment on the pattern, so they can be reviewed.
- Never silently drop or auto-fix a saying. Flag it and report the count.

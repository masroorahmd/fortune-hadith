# fortune-hadith

A `fortune` for hadith. It prints a saying of the Prophet Muhammad(saw),
chosen at random, the way `fortune(6)` prints a cookie.

```console
$ hadith
Heaven lies at the feet of mothers.
        -- The Sayings of Muhammad(saw), No. 309 (Mothers)

$ hadith --1905
Heaven lieth at the feet of mothers.
        -- The Sayings of Muhammad(saw), No. 309 (Mothers)
```

The point of the project is distribution through the normal channels —
`apt install hadith`, and from there the other distributions. That goal, not
the code, is what drives most of the decisions here.

## Install

Not yet in any archive. Build it yourself:

```console
$ sudo apt install debhelper fortune-mod python3
$ ./tools/build-deb.sh /tmp/hadith-build
$ sudo dpkg -i /tmp/hadith-build/fortunes-hadith_*.deb /tmp/hadith-build/hadith_*.deb
```

One source, two packages, the way `bible-kjv` splits from `bible-kjv-text`:

| | |
|---|---|
| `fortunes-hadith` | the cookie files. Install this alone and `fortune` draws from them along with everything else you have. |
| `hadith` | the command. Draws from these two corpora only, and makes the modernised text the default. |

Or skip the package entirely — the corpora are ordinary fortune cookie files:

```console
$ python3 tools/make_fortune.py --src corpus/suhrawardy-modern.jsonl \
      --field modern --out fortune/hadith-suhrawardy
$ strfile fortune/hadith-suhrawardy
$ fortune "$PWD/fortune/hadith-suhrawardy"
```

Use an absolute path there. Given a relative one, fortune 1.99 prints two
spurious errors about a search path it tried first, and then works anyway.

## Usage

```
hadith                    a saying, in modern wording
hadith --1905             the same corpus as Suhrawardy set it in 1905
hadith --both             draw from both, each equally likely
hadith -s                 short sayings only (160 of the 443)
hadith -m 'mother'        every saying that mentions mothers
```

Anything not in that list is passed to `fortune(6)`, so its options work here
too. Full detail in `man 6 hadith`.

`fortunes-hadith` puts both corpora in `/usr/share/games/fortunes`, so plain
`fortune` draws from them too. Be aware that fortune weights by file size: the
two hadith files together are larger than Debian's `fortunes`, `literature` and
`riddles` combined, so they will come up about half the time.

## The corpus

*The Sayings of Muhammad*, collected and translated by **Abdullah al-Mamun
al-Suhrawardy** and published in **1905**: 439 sayings arranged over 85 topics,
plus four the book prints in its preamble. The median saying is 126 characters
long, 186 once the attribution line is on it, which is why the format suits
`fortune` so well.

It is in the public domain — the author died in 1935, and the book was
published before 1930. That is not incidental. Debian's ftp-master checks
`debian/copyright` for *every file in the package, data as well as code*, so a
corpus under "personal, noncommercial use" terms cannot ship at all, not even
to `non-free`. See [DATA-LICENSE.md](DATA-LICENSE.md).

### Two corpora, and why

Suhrawardy's English is Victorian. `payeth`, `thou` and `verily` are what a
reader meets first, and they make a living text read as a museum piece. 256 of
the 443 entries needed changing; 64 of those needed a human.

So the shipped default is a **modernisation**, and the 1905 wording is
installed beside it unaltered:

```
/usr/share/games/fortunes/hadith-suhrawardy        modern — the default
/usr/share/games/fortunes/hadith-suhrawardy-1905   the original
```

Keeping both is what makes the modernisation defensible where a fresh
translation from the Arabic would not be. The semantic work was done by a human
in 1905; the change of register is ours, it sits next to what it changed, and
every divergence is a diff a reader can check. Word-level substitutions are
derived mechanically against the system dictionary; the 64 places where that
was not enough are hand-written in `corpus/modernised.tsv`.

`tools/modernise_check.py` compares the two mechanically — proper names,
numerals, content words, length ratio, leftover archaisms, and British against
American spelling. That last one earned its place: a model pass introduced
`fulfill`, `rumors` and `recognize` into a text that spells `splendour` and
`honoureth` throughout, and no content check would ever have seen it.

## Pipeline

```
tools/parse_suhrawardy.py   raw OCR   -> corpus/suhrawardy-1905.jsonl
tools/qa.py                 merges recovered.tsv, applies corrections.tsv and
                            artefacts.tsv, flags what needs a human, sweeps
                            for debris
tools/modernise.py          1905 text -> corpus/suhrawardy-modern.jsonl
tools/modernise_check.py    does the modern text still say the same thing
tools/make_fortune.py       jsonl     -> fortune/hadith-suhrawardy
```

Run in that order — `qa.py` rewrites the JSONL in place, and `modernise.py`
reads what it wrote. Everything is Python 3 standard library; nothing needs the
network.

The JSONL under `corpus/` is committed, so you do not need to run any of this
to build the package. `debian/rules` calls only the last step.

`corpus/raw/` is gitignored. The sayings themselves are public domain and are
committed; the raw OCR dumps are not, because they also carry the reprint's
preface and introduction, which are still in copyright.

### The repair layers

Three data files carry what the scan could not give up, all keyed by saying
number and all recording the page so a reader can check them:

| File | What it holds |
|---|---|
| `corpus/recovered.tsv` | 25 sayings the OCR lost outright, read off the page images |
| `corpus/proofed.tsv` | 50 entries transcribed whole, where OCR merged foreign material in |
| `corpus/artefacts.tsv` | 71 anchored single edits removing debris, every one checked against the image, plus 8 lines recording an entry that was flagged, opened at the page, and is right as printed |
| `corpus/corrections.tsv` | 94 word-level OCR substitutions, each with the pattern it belongs to |

Each has a guarantee that keeps it from rotting. A `recovered.tsv` line that
starts parsing on its own is reported as redundant rather than silently
overwriting, so a stale transcription cannot outlive the defect it worked
around. An `artefacts.tsv` anchor must match **exactly once** — zero matches
means the repair is stale, more than one means it would be a guess, and neither
is applied.

Corrections to the corpus are data, not code. They belong in a TSV with a
comment on the pattern, so that they can be reviewed.

## Contributing

The one rule that matters: **never silently drop or auto-fix a saying.** Flag
it and report the count. A misattributed hadith is not a cosmetic defect.

Anything touching the corpus should be anchored to the page image, not to what
a second OCR pass says. Two passes agreeing is evidence, not proof — saying 291
is `noble`, one pass reads `goble` and the other `jioble`, and the right answer
is in neither.

Anything touching `debian/` should keep `lintian --profile debian --pedantic`
quiet. Note that Ubuntu's lintian profile reports `unstable` as a bad
distribution; that is correct and expected, since this targets Debian.

## Licence

| | |
|---|---|
| Code (`tools/`, `bin/`, `debian/`) | GPL-3.0-or-later |
| 1905 text and its transcriptions | public domain |
| The modernisation | CC0-1.0 |

Full statement per file in [DATA-LICENSE.md](DATA-LICENSE.md) and
`debian/copyright`.

## Status

Packaged and lintian-clean; not yet uploaded anywhere. Debian needs an ITP bug
and a sponsor via `mentors.debian.net`, which is realistically months. A PPA,
the AUR and openSUSE OBS are days.

A second public-domain corpus is identified and not yet processed: Lane-Poole,
*The Speeches & Table-Talk of the Prophet Mohammad* (1882). The package is
built multi-corpus from the start so that adding it is a data change rather
than a rebuild.

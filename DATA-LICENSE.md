# Licence of the corpus data

The code in this repository and the text it ships are under different terms.
This file states them per file, so that the question can be answered without
reading `debian/copyright`.

| File | Holder | Licence |
|---|---|---|
| `corpus/suhrawardy-1905.jsonl` | Abdullah al-Mamun al-Suhrawardy, 1905 | public domain |
| `corpus/recovered.tsv` | ″ | public domain |
| `corpus/proofed.tsv` | ″ | public domain |
| `corpus/corrections.tsv` | ″ | public domain |
| `corpus/artefacts.tsv` | ″ | public domain |
| `corpus/suhrawardy-modern.jsonl` | this project, 2026 | CC0-1.0 |
| `corpus/modernised.tsv` | ″ | CC0-1.0 |
| `corpus/modern-lexicon.tsv` | ″ | CC0-1.0 |
| `tools/`, `bin/`, `pilot/`, `debian/` | this project, 2026 | GPL-3.0-or-later |

## Why the 1905 text is free to distribute

*The Sayings of Muhammad*, Abdullah al-Mamun al-Suhrawardy, published 1905.
The author died in 1935.

- **United States** — published before 1930, so public domain there outright.
- **European Union, including Germany** — 70 years *post mortem auctoris*,
  which ran out at the end of 2005.
- **United Kingdom**, where it was published — the same 70 years p.m.a.

The translation is the part that could hold a copyright of its own, and it is
Suhrawardy's. No estate or successor holds a right in it.

The source scan, `archive.org/details/the-sayings-of-muhammad_202401`, is of a
**later reprint**. Only the 1905 sayings are taken from it. The reprint's own
preface and introduction are under their own copyright and are excluded by the
parser; nothing of them is in this repository or in the package.

## Why the transcription tables are listed as public domain too

`recovered.tsv`, `proofed.tsv`, `corrections.tsv` and `artefacts.tsv` hold
nothing but readings of that same book — sayings the OCR destroyed, retyped
from the page images, and the anchored edits that undo scanning damage.
Faithful transcription of a public-domain text creates no new copyright. They
are listed so that every file is accounted for, not because they add a claim.

## The modernisation is separate work

The modernisation of the Victorian English is this project's own, and is
dedicated to the public domain under CC0-1.0. The 1905 wording is kept beside
it in `corpus/suhrawardy-1905.jsonl`, which is what makes that claim checkable:
the whole of the change is a diff.

## What is deliberately not here

Several modern hadith collections and translations were consulted while this
corpus was prepared, to check a reading or settle an ambiguous word. **None of
them is redistributed here, and no phrasing was adopted from any of them.**
Their terms typically permit download for personal, noncommercial use and not
republication, so consulting them is fine and shipping them would not be.
`reference/` and `corpus/raw/` are gitignored for that reason.

The same goes for the modern English translations that circulate inside
aggregator repositories. An aggregator's own permissive licence file does not
reach the translations underneath it — *nemo dat quod non habet* — and no text
from one is used here.

Everything this package ships descends from the 1905 book and from our own
modernisation of it. That is the whole provenance, and it is why the licence
question has a short answer.

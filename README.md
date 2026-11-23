# The Morning Atlas — Monday 23 November 2026

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/Yuu078/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/Yuu078/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

A single newspaper page that fits the whole world's news of **Monday
23 November 2026** into one 1024×1024 image: 35 stories from 7 regions.
The lead story is the COP31 climate talks collapsing in Antalya with
zero fossil-fuel mentions in the final draft.

This repository is an entry for the [make.fun](https://make.fun/bounty/news-image-20261123)
bounty **news-image-20261123** — "Sum up 23 November's world news in
one image".

## Files in this repo

- `entry.png` — the poster, a 1024×1024 PNG under the 1 MiB cap.
- `render_atlas_v6.py` — draws the poster from a data ledger of 35
  stories: masthead, a four-number strip (0, 15, 258, 24), a hero card
  showing an empty summit hall under a giant red 0, nine illustrated
  story cards in a 3×3 grid, THE WIRE with the other 25 stories in two
  columns, region chips, and a DATE CHECK box listing two near-miss
  stories we deliberately left out. Pillow only; run it twice and the
  output bytes are identical.
- `main.py` — the entry point. It copies the committed `entry.png`
  byte-for-byte into `MAKEFUN_OUTPUT_DIR` (or `/output` by default)
  and checks the copy's SHA-256 against the original.
- `stories.md` lives next to the repo in the build folder — 35 stories
  with headline, region, source and a 15–25 word summary each. Five
  of them were spot-checked against live sources before the build;
  three near-miss candidates were rejected for the wrong date and
  replaced.

## Running it

```sh
python3 render_atlas_v6.py                    # rebuild entry.png
MAKEFUN_OUTPUT_DIR=out python3 main.py       # deliver out/entry.png
```

## Licence

MIT — see `LICENSE`.

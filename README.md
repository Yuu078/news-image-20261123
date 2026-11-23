# news-image-20261123 — THE MORNING ATLAS

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/Yuu078/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/Yuu078/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

One-page newspaper poster summing up the world's news of **Monday 23 November 2026**:
35 stories across 7 regions, led by the collapse of the COP31 climate talks in Antalya.

Built for the [make.fun](https://make.fun/bounty/news-image-20261123) bounty
**news-image-20261123** ("Sum up 23 November's world news in one image").

## What it is

- `entry.png` — the poster itself, 1024×1024 PNG.
- `render_atlas_v6.py` — the program that draws the poster from scratch
  with Pillow (masthead, 4-number strip, hero card with an empty summit
  hall under a giant 0, 9 fully illustrated story cards in a 3×3 grid,
  a 25-line THE WIRE in two columns, a region chip row generated from
  the story ledger, DATE CHECK). Run it twice and the bytes are identical.
- `main.py` — the entry program: it copies the committed `entry.png`
  byte-for-byte to `MAKEFUN_OUTPUT_DIR` (default `/output`), verifying
  size and SHA-256 of the delivered copy.

## How to run

```sh
python3 render_atlas_v6.py   # rebuild entry.png (deterministic)
MAKEFUN_OUTPUT_DIR=out python3 main.py   # write out/entry.png
```

## Story list

See `../stories.md` (35 stories with headline, region, source and a
15–25 word summary each; 5 random stories spot-checked against live
sources before the build).

## License

MIT — see `LICENSE`.

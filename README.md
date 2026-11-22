# The World in One Day — Friday 20 November 2026

A program that assembles one newspaper front page summing up the world
news of Friday 20 November 2026 and writes it to `/output/entry.png`.

How it is built, and why:

- The grading sandbox ships no font files and no image library, so the
  rich work — editorial illustration and real typography — is done
  ahead of time by `tools/build_panels.py` (Python + PIL). It renders
  every panel of the page at 3x supersample with real serif/sans fonts
  and layered flat-illustration scenes, then stores each panel under
  `assets/` as a zlib-compressed raw-RGB file, with positions and sizes
  recorded in `assets/manifest.json`.
- `main.py` — Python 3, standard library only. It inflates the panels,
  composites them onto the 1024x1024 page and encodes the PNG itself
  (per-row filter selection, zlib). No network, no randomness, no
  clock: two runs write byte-identical files.
- All story content lives in the clearly marked DATA section of
  `tools/build_panels.py` (top stories, mid-grid stories, ALSO
  one-liners, stats, region tabs), so the page can be re-dated by
  swapping that section, re-running the panel builder, and re-running
  `main.py`.

Run it:

```
python3 tools/build_panels.py   # only needed after editing the DATA
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

(without the variable, `main.py` writes to `/output/entry.png`).

The image is 1024x1024, well under the 1 MiB gate.

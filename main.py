#!/usr/bin/env python3
"""
The World in One Day -- Friday 20 November 2026 (entry program).

Standard library only. The rich illustration and typography of this
page were pre-rendered with full tooling by tools/build_panels.py into
panel assets under assets/ (zlib-compressed raw RGB + manifest.json).
This program inflates the panels, composites them onto the 1024x1024
page and encodes the PNG itself. No network, no randomness, no clock:
two runs write byte-identical files.

Output: $MAKEFUN_OUTPUT_DIR/entry.png, or /output/entry.png.
"""

import json
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")


def composite(manifest):
    """Paste every panel onto the page canvas; returns (w, h, bytearray)."""
    w, h = manifest["canvas"]
    bg = bytes(manifest["background"])
    canvas = bytearray(bg * (w * h))
    for panel in manifest["panels"]:
        pw, ph = panel["w"], panel["h"]
        with open(os.path.join(ASSETS, panel["file"]), "rb") as f:
            raw = zlib.decompress(f.read())
        if len(raw) != pw * ph * 3:
            raise ValueError("panel size mismatch: " + panel["file"])
        x0, y0 = panel["x"], panel["y"]
        row_bytes = pw * 3
        for row in range(ph):
            src = raw[row * row_bytes:(row + 1) * row_bytes]
            dst = ((y0 + row) * w + x0) * 3
            canvas[dst:dst + row_bytes] = src
    return w, h, canvas


def _score(data, step=5):
    """PNG filter heuristic: sum of signed-byte magnitudes, sampled."""
    total = 0
    for i in range(0, len(data), step):
        b = data[i]
        total += b if b < 128 else 256 - b
    return total


def _sub_row(cur):
    left = b"\x00\x00\x00" + cur[:-3]
    return bytes((a - b) & 0xFF for a, b in zip(cur, left))


def _up_row(cur, prev):
    return bytes((a - b) & 0xFF for a, b in zip(cur, prev))


def encode_png(w, h, rgb):
    """Encode RGB bytes as a PNG, choosing a filter per row."""
    stride = w * 3
    out = bytearray()
    prev = bytes(stride)
    for y in range(h):
        cur = bytes(rgb[y * stride:(y + 1) * stride])
        # sampled scores for the three candidate filters
        s_none = _score(cur)
        s_sub = 0
        for i in range(0, stride, 5):
            b = (cur[i] - (cur[i - 3] if i >= 3 else 0)) & 0xFF
            s_sub += b if b < 128 else 256 - b
        s_up = 0
        for i in range(0, stride, 5):
            b = (cur[i] - prev[i]) & 0xFF
            s_up += b if b < 128 else 256 - b
        best = min((s_none, 0), (s_sub, 1), (s_up, 2))[1]
        if best == 0:
            out.append(0)
            out += cur
        elif best == 1:
            out.append(1)
            out += _sub_row(cur)
        else:
            out.append(2)
            out += _up_row(cur, prev)
        prev = cur
    idat = zlib.compress(bytes(out), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", idat)
    png += chunk(b"IEND", b"")
    return png


def main():
    with open(os.path.join(ASSETS, "manifest.json")) as f:
        manifest = json.load(f)
    w, h, canvas = composite(manifest)
    png = encode_png(w, h, canvas)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    print(f"wrote {path} ({len(png)} bytes)")


if __name__ == "__main__":
    main()

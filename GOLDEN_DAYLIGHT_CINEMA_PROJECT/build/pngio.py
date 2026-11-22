"""
pngio.py -- minimal, dependency-free 16-bit RGB PNG reader/writer.

Pillow cannot write 16-bit-per-channel RGB PNGs, and the simulated Apple Log 2
intermediates must keep more than 8-bit precision to be worth storing.  This
module writes/reads plain PNG (colour type 2, bit depth 16, no interlace) with
zlib, using numpy for the filtering.  It is intentionally small and exact:
the round-trip test in gdc_validate.py requires bit equality.
"""

from __future__ import annotations

import struct
import zlib

import numpy as np


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png_rgb16(path: str, arr: np.ndarray) -> None:
    """arr: (H, W, 3) uint16 -> 16-bit RGB PNG."""
    arr = np.ascontiguousarray(arr.astype(np.uint16))
    h, w, _ = arr.shape
    raw = np.empty((h, 1 + w * 3 * 2), dtype=np.uint8)
    raw[:, 0] = 0                                  # filter type 0 (None)
    be = arr.astype(">u2").view(np.uint8).reshape(h, w * 6)
    raw[:, 1:] = be
    ihdr = struct.pack(">IIBBBBB", w, h, 16, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(raw.tobytes(), 9))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def write_png_rgb8(path: str, arr: np.ndarray, adaptive: bool = True) -> None:
    """arr: (H, W, 3) uint8 -> 8-bit RGB PNG.

    With ``adaptive`` the per-row filter (None/Sub/Up/Average/Paeth) is chosen by
    the usual minimum-sum-of-absolute-differences heuristic, which roughly halves
    the file size of photographic PNGs compared with filter 0.
    """
    arr = np.ascontiguousarray(arr.astype(np.uint8))
    h, w, _ = arr.shape
    bpp = 3
    lines = arr.reshape(h, w * 3).astype(np.int16)
    raw = np.zeros((h, 1 + w * 3), dtype=np.uint8)
    prev = np.zeros(w * 3, dtype=np.int16)
    for y in range(h):
        cur = lines[y]
        if not adaptive:
            raw[y, 1:] = cur.astype(np.uint8)
            prev = cur
            continue
        left = np.concatenate([np.zeros(bpp, np.int16), cur[:-bpp]])
        up = prev
        upleft = np.concatenate([np.zeros(bpp, np.int16), prev[:-bpp]])
        cand = [
            cur,
            cur - left,
            cur - up,
            cur - ((left + up) >> 1),
            cur - _paeth(left.astype(np.uint8), up.astype(np.uint8),
                         upleft.astype(np.uint8)).astype(np.int16),
        ]
        costs = [np.abs(c.astype(np.int8).astype(np.int32)).sum() for c in cand]
        f = int(np.argmin(costs))
        raw[y, 0] = f
        raw[y, 1:] = cand[f].astype(np.uint8)
        prev = cur
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(raw.tobytes(), 9))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def _iter_chunks(data: bytes):
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    i = 8
    while i < len(data):
        (n,) = struct.unpack(">I", data[i:i + 4])
        tag = data[i + 4:i + 8]
        payload = data[i + 8:i + 8 + n]
        yield tag, payload
        i += 12 + n


def _paeth(a, b, c):
    p = a.astype(np.int32) + b.astype(np.int32) - c.astype(np.int32)
    pa = np.abs(p - a)
    pb = np.abs(p - b)
    pc = np.abs(p - c)
    return np.where((pa <= pb) & (pa <= pc), a,
                    np.where(pb <= pc, b, c)).astype(np.uint8)


def read_png(path: str) -> np.ndarray:
    """Read a non-interlaced RGB PNG. Returns uint8 (8-bit) or uint16 (16-bit)."""
    with open(path, "rb") as f:
        data = f.read()
    w = h = depth = None
    idat = bytearray()
    for tag, payload in _iter_chunks(data):
        if tag == b"IHDR":
            w, h, depth, ctype, comp, filt, inter = struct.unpack(">IIBBBBB", payload)
            assert ctype == 2, f"only RGB PNG supported (ctype={ctype})"
            assert inter == 0, "interlaced PNG not supported"
        elif tag == b"IDAT":
            idat += payload
    bpp = 3 * (depth // 8)
    stride = w * bpp
    raw = np.frombuffer(zlib.decompress(bytes(idat)), dtype=np.uint8)
    raw = raw.reshape(h, stride + 1)
    out = np.zeros((h, stride), dtype=np.uint8)
    prev = np.zeros(stride, dtype=np.uint8)
    for y in range(h):
        f = raw[y, 0]
        line = raw[y, 1:]
        if f == 0:
            cur = line.copy()
        elif f == 1:
            cur = line.copy()
            for x in range(bpp, stride):
                cur[x] = (int(cur[x]) + int(cur[x - bpp])) & 0xFF
        elif f == 2:
            cur = (line.astype(np.int32) + prev.astype(np.int32)).astype(np.uint8)
        elif f == 3:
            cur = line.copy()
            for x in range(stride):
                left = int(cur[x - bpp]) if x >= bpp else 0
                cur[x] = (int(cur[x]) + ((left + int(prev[x])) >> 1)) & 0xFF
        elif f == 4:
            cur = line.copy()
            for x in range(stride):
                left = cur[x - bpp] if x >= bpp else np.uint8(0)
                upleft = prev[x - bpp] if x >= bpp else np.uint8(0)
                cur[x] = (int(cur[x]) + int(_paeth(np.array([left]), np.array([prev[x]]),
                                                   np.array([upleft]))[0])) & 0xFF
        else:
            raise ValueError(f"bad filter {f}")
        out[y] = cur
        prev = cur
    if depth == 16:
        return out.view(">u2").astype(np.uint16).reshape(h, w, 3)
    return out.reshape(h, w, 3)


if __name__ == "__main__":
    rng = np.random.default_rng(1)
    a = rng.integers(0, 65536, (17, 23, 3), dtype=np.uint16)
    write_png_rgb16("/tmp/t16.png", a)
    b = read_png("/tmp/t16.png")
    print("16-bit round trip exact:", np.array_equal(a, b))
    a8 = rng.integers(0, 256, (17, 23, 3), dtype=np.uint8)
    write_png_rgb8("/tmp/t8.png", a8)
    print("8-bit round trip exact:", np.array_equal(a8, read_png("/tmp/t8.png")))

#!/usr/bin/env python3
"""Read and trilinearly evaluate a 3D .cube LUT (pure numpy)."""
import numpy as np


class CubeLUT:
    def __init__(self, path):
        self.path = path
        self.size = None
        self.data = None
        self._parse(path)

    def _parse(self, path):
        entries = []
        size = None
        with open(path) as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                parts = s.split()
                if parts[0] == "LUT_3D_SIZE":
                    size = int(parts[1])
                elif parts[0] == "TITLE":
                    continue
                elif len(parts) == 3:
                    try:
                        entries.append((float(parts[0]), float(parts[1]), float(parts[2])))
                    except ValueError:
                        pass
        if size is None:
            raise ValueError("No LUT_3D_SIZE found")
        n = size ** 3
        if len(entries) != n:
            raise ValueError(f"Expected {n} entries, found {len(entries)}")
        self.size = size
        self.data = np.array(entries, dtype=np.float64).reshape(size, size, size, 3)

    def __call__(self, rgb):
        rgb = np.asarray(rgb, dtype=np.float64)
        shape = rgb.shape
        flat = np.clip(rgb.reshape(-1, 3), 0.0, 1.0)
        n = self.size
        coord = flat * (n - 1)
        i0 = np.floor(coord).astype(np.int64)
        tx = coord - i0
        i1 = np.minimum(i0 + 1, n - 1)

        out = np.zeros_like(flat)
        for di in (0, 1):
            for dj in (0, 1):
                for dk in (0, 1):
                    w = ((1.0 - tx[:, 0]) if di == 0 else tx[:, 0]) * \
                        ((1.0 - tx[:, 1]) if dj == 0 else tx[:, 1]) * \
                        ((1.0 - tx[:, 2]) if dk == 0 else tx[:, 2])
                    ii = np.minimum(i0[:, 0] + di, n - 1)
                    jj = np.minimum(i0[:, 1] + dj, n - 1)
                    kk = np.minimum(i0[:, 2] + dk, n - 1)
                    out += w[:, None] * self.data[ii, jj, kk, :]
        return out.reshape(shape)


if __name__ == "__main__":
    import sys
    lut = CubeLUT(sys.argv[1])
    print("size", lut.size, "shape", lut.data.shape)
    print("black", lut(np.array([0.0, 0.0, 0.0])))
    print("mid  ", lut(np.array([0.5, 0.5, 0.5])))
    print("white", lut(np.array([1.0, 1.0, 1.0])))

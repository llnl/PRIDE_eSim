#!/usr/bin/env python3
"""Generate synthetic 3D-printer samples for an extruded logo.

The CSV columns are x, y, z, and ink_flow; ``diw_post.py`` consumes this CSV.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath


def _seed(part_number: str) -> int:
    digest = hashlib.sha256(part_number.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little") % (2**32)


def _filled_logo_points(logo: str) -> np.ndarray:
    """Return a dense, ordered point set inside a bold text outline."""
    text_path = TextPath((0, 0), logo, size=10,
                         prop=FontProperties(family="DejaVu Sans", weight="bold"))
    bounds = text_path.get_extents()
    x_axis = np.linspace(bounds.xmin, bounds.xmax, 320)
    y_axis = np.linspace(bounds.ymin, bounds.ymax, 80)
    xx, yy = np.meshgrid(x_axis, y_axis)
    inside = text_path.contains_points(np.column_stack((xx.ravel(), yy.ravel()))).reshape(xx.shape)

    rows = []
    for row_number in range(len(y_axis)):
        row_x = x_axis[inside[row_number]]
        if row_number % 2:
            row_x = row_x[::-1]
        rows.extend((x_value, y_axis[row_number]) for x_value in row_x)
    points = np.asarray(rows, dtype=float)
    scale = 4.0 / max(bounds.height, 1e-12)
    points[:, 0] = (points[:, 0] - bounds.xmin) * scale
    points[:, 1] = (points[:, 1] - bounds.ymin) * scale
    return points


def generate_diw_data(part_number: str, samples: int = 1000, logo: str | None = None) -> np.ndarray:
    """Return an ``(samples, 4)`` array containing x, y, z, and ink flow.

    The part number selects a repeatable path shape, which makes generated data
    stable across runs while still allowing different parts to be simulated.
    """
    if samples < 2:
        raise ValueError("samples must be at least 2")

    logo = logo or (part_number if part_number in {"LLNL", "llnl", "Siemens"} else "LLNL")
    if logo not in {"LLNL", "llnl", "Siemens"}:
        raise ValueError("logo must be LLNL, llnl, or Siemens")
    rng = np.random.default_rng(_seed(part_number + logo))
    planar = _filled_logo_points(logo)
    base = np.vstack([np.column_stack((planar, np.full(len(planar), height)))
                      for height in np.linspace(0.0, 1.6, 5)])
    indices = np.linspace(0, len(base) - 1, samples).round().astype(int)
    x, y, z = base[indices].T
    x += rng.normal(0, 0.002, samples)
    y += rng.normal(0, 0.002, samples)
    ink_flow = np.clip(1.0 + rng.normal(0, 0.02, samples), 0.01, None)
    return np.column_stack((x, y, z, ink_flow))


def write_csv(path: str | Path, data: np.ndarray) -> None:
    with Path(path).open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("x", "y", "z", "ink_flow"))
        writer.writerows(data.tolist())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part_number", required=True, help="part identifier used to seed the model")
    parser.add_argument("--logo", choices=("LLNL", "llnl", "Siemens"), default=None)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--output", default="diw.csv")
    args = parser.parse_args()
    write_csv(args.output, generate_diw_data(args.part_number, args.samples, args.logo))


if __name__ == "__main__":
    main()

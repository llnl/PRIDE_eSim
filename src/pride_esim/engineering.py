#!/usr/bin/env python3
"""Convert polar material data into a triangular printed-part mesh."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes


def read_polar_csv(path: str | Path) -> np.ndarray:
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        amount_name = "material_amount" if "material_amount" in (reader.fieldnames or ()) else "density"
        required = {"r", "theta", "z", amount_name}
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError("CSV must contain r, theta, z, density columns")
        return np.array(
            [[float(row[name]) for name in ("r", "theta", "z", amount_name)] for row in reader],
            dtype=float,
        )


def polar_to_arrays(data: np.ndarray) -> tuple[np.ndarray, ...]:
    r, theta, z, density = data.T
    return r * np.cos(theta), r * np.sin(theta), z, density


def make_mesh(x: np.ndarray, y: np.ndarray, z: np.ndarray, amount: np.ndarray,
              nx: int, ny: int, nz: int, level: float) -> tuple[np.ndarray, ...]:
    """Voxelize the printed paths and extract a closed triangular surface."""
    padding = 0.6
    axes = (
        np.linspace(x.min() - padding, x.max() + padding, nx),
        np.linspace(y.min() - padding, y.max() + padding, ny),
        np.linspace(z.min() - padding, z.max() + padding, nz),
    )
    seed = np.zeros((nx, ny, nz), dtype=float)
    ix = np.clip(np.searchsorted(axes[0], x), 0, nx - 1)
    iy = np.clip(np.searchsorted(axes[1], y), 0, ny - 1)
    iz = np.clip(np.searchsorted(axes[2], z), 0, nz - 1)
    np.maximum.at(seed, (ix, iy, iz), 1.0)
    field = gaussian_filter(seed, sigma=(1.4, 1.4, 2.0))
    field /= max(field.max(), 1e-12)
    index_vertices, faces, _, _ = marching_cubes(field, level=level)
    vertices = np.column_stack(tuple(np.interp(index_vertices[:, i], np.arange(len(axis)), axis)
                                     for i, axis in enumerate(axes)))
    return vertices, faces.astype(np.int32), field, *axes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--polar_csv", required=True)
    parser.add_argument("--output", default="engineering_arrays.npz")
    parser.add_argument("--nx", type=int, default=180)
    parser.add_argument("--ny", type=int, default=40)
    parser.add_argument("--nz", type=int, default=24)
    parser.add_argument("--level", type=float, default=0.18)
    args = parser.parse_args()
    x, y, z, amount = polar_to_arrays(read_polar_csv(args.polar_csv))
    vertices, faces, field, grid_x, grid_y, grid_z = make_mesh(
        x, y, z, amount, args.nx, args.ny, args.nz, args.level)
    np.savez_compressed(args.output, x=x, y=y, z=z,
                        material_amount=amount, vertices=vertices, faces=faces,
                        field=field, grid_x=grid_x, grid_y=grid_y, grid_z=grid_z)


if __name__ == "__main__":
    main()
